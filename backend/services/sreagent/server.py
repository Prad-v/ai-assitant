"""FastAPI web server for SRE Agent."""

import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import create_sre_agent
from .security_scanner import SecurityScanner
from .database import init_database
from .settings_service import SettingsService
from .auth import require_auth, require_admin, get_current_user
from .user_service import UserService
from .token_service import TokenService
from .session_service import SessionService
from .jwt_auth import create_jwt_token, refresh_jwt_token
from .auth_utils import verify_password
from .init_auth import init_default_admin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
APP_NAME = os.getenv("APP_NAME", "sreagent")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
CLUSTER_INVENTORY_SERVICE_URL = os.getenv("CLUSTER_INVENTORY_SERVICE_URL", "http://cluster-inventory:8001")

# Initialize FastAPI app
app = FastAPI(
    title="SRE Agent API",
    description="Kubernetes Troubleshooting Chat Agent with MCP Integration",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global session service and agent
session_service: Optional[InMemorySessionService] = None
agent: Optional[Agent] = None
runner: Optional[Runner] = None
security_scanner: Optional[SecurityScanner] = None


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    cluster_id: Optional[str] = None  # Cluster context for multi-cluster support


class ChatResponse(BaseModel):
    response: str
    session_id: str


class HealthResponse(BaseModel):
    status: str
    agent_ready: bool
    mcp_connected: bool


@app.on_event("startup")
async def startup_event():
    """Initialize agent and MCP connection on startup."""
    global session_service, agent, runner, security_scanner
    
    logger.info("Initializing SRE Agent...")
    
    try:
        # Initialize database
        if not init_database():
            logger.warning("Database initialization failed. Some features may not work.")
        else:
            # Initialize default admin account
            init_default_admin()
        
        # Initialize session service
        session_service = InMemorySessionService()
        
        # Initialize security scanner
        global security_scanner
        security_scanner = SecurityScanner(cluster_inventory_service_url=CLUSTER_INVENTORY_SERVICE_URL)
        logger.info("Security scanner initialized")
        
        # Create agent (MCP tools are initialized internally)
        logger.info("Initializing agent with MCP tools...")
        agent = create_sre_agent()
        logger.info(f"Agent initialized with {len(agent.tools) if agent.tools else 0} tools.")
        
        # Create runner
        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=session_service,
        )
        
        logger.info("SRE Agent initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        # Create agent without MCP tools as fallback
        agent = create_sre_agent()
        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=InMemorySessionService(),
        )
        logger.warning("Agent initialized (MCP tools may not be available)")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        agent_ready=agent is not None and runner is not None,
        mcp_connected=agent is not None and agent.tools is not None and len(agent.tools) > 0,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(require_auth)):
    """Chat endpoint for interacting with the agent."""
    if not agent or not runner:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Get user_id from authenticated user
        user_id = str(current_user["user_id"])
        
        # Get or create session
        session_id = request.session_id
        if not session_id:
            session_id = f"session_{user_id}"
        
        # Ensure session exists before running agent
        # The Runner expects the session to already exist, so we must create it first
        try:
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )
            logger.info(f"Using existing session: {session_id}")
        except Exception as e:
            # Create new session if it doesn't exist
            logger.info(f"Creating new session: {session_id} (error: {e})")
            try:
                session = await session_service.create_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                )
                logger.info(f"Session created successfully: {session_id}")
            except Exception as create_error:
                logger.error(f"Failed to create session: {create_error}")
                raise HTTPException(status_code=500, detail=f"Failed to create session: {create_error}")
        
        # Verify session exists by trying to get it again
        try:
            await session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )
            logger.info(f"Session verified: {session_id}")
        except Exception as verify_error:
            logger.error(f"Session verification failed: {verify_error}")
            raise HTTPException(status_code=500, detail=f"Session not available: {verify_error}")
        
        # Create user message
        content = types.Content(
            role="user",
            parts=[types.Part(text=request.message)],
        )
        
        # Run agent using async method to properly handle session access
        logger.info(f"Running agent for session: {session_id}, user: {user_id}")
        try:
            # Use run_async instead of run to properly handle async session operations
            events = []
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
            ):
                events.append(event)
            logger.info(f"Collected {len(events)} events from agent")
        except ValueError as ve:
            if "Session not found" in str(ve):
                logger.error(f"Session not found error: {ve}. Attempting to recreate session...")
                # Try to create the session again and retry
                try:
                    await session_service.create_session(
                        app_name=APP_NAME,
                        user_id=user_id,
                        session_id=session_id,
                    )
                    logger.info(f"Session recreated, retrying agent run...")
                    events = []
                    async for event in runner.run_async(
                        user_id=user_id,
                        session_id=session_id,
                        new_message=content,
                    ):
                        events.append(event)
                    logger.info(f"Retry successful, collected {len(events)} events")
                except Exception as retry_error:
                    logger.error(f"Retry failed: {retry_error}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"Agent execution failed: {retry_error}")
            else:
                logger.error(f"ValueError in agent run: {ve}", exc_info=True)
                raise
        except Exception as e:
            logger.error(f"Unexpected error in agent run: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")
        
        # Collect response from events
        response_text = ""
        event_count = 0
        for event in events:
            event_count += 1
            logger.debug(f"Event {event_count}: {type(event).__name__}, has is_final_response: {hasattr(event, 'is_final_response')}")
            
            # Check for final response
            if hasattr(event, 'is_final_response') and callable(event.is_final_response):
                if event.is_final_response():
                    logger.info(f"Found final response event")
                    if hasattr(event, 'content') and event.content:
                        if hasattr(event.content, 'parts') and event.content.parts:
                            if len(event.content.parts) > 0:
                                if hasattr(event.content.parts[0], 'text'):
                                    response_text = event.content.parts[0].text
                                    logger.info(f"Extracted response text: {len(response_text)} chars")
                                    break
            
            # Check for text attribute directly
            if hasattr(event, 'text') and event.text:
                response_text = event.text
                logger.info(f"Found text in event: {len(response_text)} chars")
                break
            
            # Check for message attribute
            if hasattr(event, 'message') and event.message:
                if hasattr(event.message, 'text'):
                    response_text = event.message.text
                    logger.info(f"Found message text: {len(response_text)} chars")
                    break
        
        logger.info(f"Processed {event_count} events, response length: {len(response_text)}")
        
        if not response_text:
            logger.warning(f"No response text generated for session: {session_id} after processing {event_count} events")
            response_text = "I received your message but couldn't generate a response."
        
        logger.info(f"Generated response for session: {session_id}")
        return ChatResponse(
            response=response_text,
            session_id=session_id,
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "SRE Agent",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "docs": "/docs",
            "security": "/security",
            "settings": "/settings/model",
            "auth": "/auth/login",
        },
    }


# Authentication endpoints
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    session_token: str
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str


class LogoutRequest(BaseModel):
    session_token: Optional[str] = None


class UserInfoResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: Optional[str] = None


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login with username and password."""
    try:
        # Get user by username
        user = UserService.get_user_by_username(request.username)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Verify password
        if not verify_password(request.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Check if user is active
        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="User account is disabled")
        
        # Update last login
        UserService.update_last_login(user["id"])
        
        # Create JWT tokens
        access_token = create_jwt_token(user["id"], user["username"], user["role"], "access")
        refresh_token = create_jwt_token(user["id"], user["username"], user["role"], "refresh")
        
        # Create session token
        session_token = SessionService.create_session(user["id"])
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            session_token=session_token,
            user={
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@app.post("/auth/refresh", response_model=RefreshResponse)
async def refresh(request: RefreshRequest):
    """Refresh JWT access token."""
    try:
        tokens = refresh_jwt_token(request.refresh_token)
        if not tokens:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        
        return RefreshResponse(**tokens)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")


@app.post("/auth/logout")
async def logout(request: LogoutRequest, current_user: dict = Depends(require_auth)):
    """Logout (invalidate session)."""
    try:
        # If session token provided in request, use it; otherwise try to get from context
        session_token = request.session_token
        if session_token:
            SessionService.invalidate_session(session_token)
            return {"message": "Logged out successfully"}
        else:
            # Could extract from header/cookie if needed
            return {"message": "Logged out successfully"}
            
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")


@app.get("/auth/me", response_model=UserInfoResponse)
async def get_current_user_info(current_user: dict = Depends(require_auth)):
    """Get current user information."""
    try:
        user = UserService.get_user(current_user["user_id"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserInfoResponse(
            id=user["id"],
            username=user["username"],
            role=user["role"],
            created_at=user.get("created_at"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")


# User management endpoints (admin only)
class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_login: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    new_password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@app.get("/users", response_model=List[UserResponse])
async def list_users(admin: dict = Depends(require_admin)):
    """List all users (admin only)."""
    try:
        users = UserService.list_users()
        return [UserResponse(**user) for user in users]
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")


@app.post("/users", response_model=UserResponse)
async def create_user(request: CreateUserRequest, admin: dict = Depends(require_admin)):
    """Create a new user (admin only)."""
    try:
        user = UserService.create_user(
            username=request.username,
            password=request.password,
            role=request.role
        )
        return UserResponse(**user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, admin: dict = Depends(require_admin)):
    """Get user details (admin only)."""
    try:
        user = UserService.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(**user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")


@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, request: UpdateUserRequest, admin: dict = Depends(require_admin)):
    """Update user (admin only)."""
    try:
        update_data = {}
        if request.username is not None:
            update_data["username"] = request.username
        if request.role is not None:
            update_data["role"] = request.role
        if request.is_active is not None:
            update_data["is_active"] = request.is_active
        
        user = UserService.update_user(user_id, **update_data)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(**user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")


@app.delete("/users/{user_id}")
async def delete_user(user_id: int, admin: dict = Depends(require_admin)):
    """Delete user (admin only)."""
    try:
        success = UserService.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


@app.post("/users/{user_id}/reset-password")
async def reset_user_password(user_id: int, request: ResetPasswordRequest, admin: dict = Depends(require_admin)):
    """Reset user password (admin only)."""
    try:
        success = UserService.reset_password(user_id, request.new_password)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "Password reset successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {str(e)}")


@app.put("/users/me/password")
async def change_password(request: ChangePasswordRequest, current_user: dict = Depends(require_auth)):
    """Change own password (requires auth)."""
    try:
        success = UserService.change_password(
            current_user["user_id"],
            request.old_password,
            request.new_password
        )
        if not success:
            raise HTTPException(status_code=400, detail="Invalid old password")
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to change password: {str(e)}")


# Token management endpoints
class CreateTokenRequest(BaseModel):
    name: str
    expires_at: Optional[str] = None  # ISO format datetime string


class TokenResponse(BaseModel):
    id: int
    name: str
    created_at: str
    last_used_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_expired: bool


class CreateTokenResponse(BaseModel):
    token: str  # Only shown once!
    token_id: int
    name: str
    created_at: str
    expires_at: Optional[str] = None


@app.get("/tokens", response_model=List[TokenResponse])
async def list_tokens(current_user: dict = Depends(require_auth)):
    """List own API tokens (requires auth)."""
    try:
        tokens = TokenService.list_api_tokens(current_user["user_id"])
        return [TokenResponse(**token) for token in tokens]
    except Exception as e:
        logger.error(f"Error listing tokens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list tokens: {str(e)}")


@app.post("/tokens", response_model=CreateTokenResponse)
async def create_token(request: CreateTokenRequest, current_user: dict = Depends(require_auth)):
    """Create new API token (requires auth)."""
    try:
        expires_at = None
        if request.expires_at:
            expires_at = datetime.fromisoformat(request.expires_at.replace('Z', '+00:00'))
        
        token_data = TokenService.create_api_token(
            user_id=current_user["user_id"],
            name=request.name,
            expires_at=expires_at
        )
        return CreateTokenResponse(**token_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create token: {str(e)}")


@app.delete("/tokens/{token_id}")
async def revoke_token(token_id: int, current_user: dict = Depends(require_auth)):
    """Revoke API token (requires auth, must own token)."""
    try:
        success = TokenService.revoke_api_token(token_id, current_user["user_id"])
        if not success:
            raise HTTPException(status_code=404, detail="Token not found or not owned by user")
        return {"message": "Token revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to revoke token: {str(e)}")


# Settings API endpoints
class ModelSettingsRequest(BaseModel):
    provider: str
    model_name: str
    api_key: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


class ModelSettingsResponse(BaseModel):
    provider: str
    model_name: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


class ValidateApiKeyRequest(BaseModel):
    provider: str
    model_name: str
    api_key: str


class ValidateApiKeyResponse(BaseModel):
    valid: bool
    message: str


class ListModelsRequest(BaseModel):
    provider: str
    api_key: str


class ListModelsResponse(BaseModel):
    success: bool
    models: List[str]
    message: str


@app.post("/settings/models/list", response_model=ListModelsResponse)
async def list_available_models(request: ListModelsRequest, admin: dict = Depends(require_admin)):
    """List available models for a provider (admin-only)."""
    try:
        logger.info(f"Listing models for provider: {request.provider}")
        result = SettingsService.list_available_models(
            provider=request.provider,
            api_key=request.api_key
        )
        logger.info(f"Model listing result: success={result.get('success')}, models_count={len(result.get('models', []))}")
        return ListModelsResponse(**result)
    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@app.post("/settings/model/validate", response_model=ValidateApiKeyResponse)
async def validate_api_key(request: ValidateApiKeyRequest, admin: dict = Depends(require_admin)):
    """Validate API key without saving (admin-only)."""
    try:
        result = SettingsService.validate_api_key(
            provider=request.provider,
            model_name=request.model_name,
            api_key=request.api_key
        )
        return ValidateApiKeyResponse(**result)
    except Exception as e:
        logger.error(f"Error validating API key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate API key: {str(e)}")


@app.get("/settings/model", response_model=ModelSettingsResponse)
async def get_model_settings(admin: dict = Depends(require_admin)):
    """Get current model settings (admin-only)."""
    try:
        settings = SettingsService.get_model_settings()
        if not settings:
            raise HTTPException(status_code=404, detail="Model settings not configured")
        return ModelSettingsResponse(**settings)
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) as-is
        raise
    except Exception as e:
        logger.error(f"Error getting model settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get model settings: {str(e)}")


@app.put("/settings/model", response_model=ModelSettingsResponse)
async def update_model_settings(request: ModelSettingsRequest, admin: dict = Depends(require_admin)):
    """Update model settings (admin-only, validates API key before saving)."""
    try:
        # Validate API key first
        validation_result = SettingsService.validate_api_key(
            provider=request.provider,
            model_name=request.model_name,
            api_key=request.api_key
        )
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"API key validation failed: {validation_result['message']}"
            )
        
        # Update settings
        success = SettingsService.update_model_settings(
            provider=request.provider,
            model_name=request.model_name,
            api_key=request.api_key,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            updated_by="admin"  # TODO: Get from auth context
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update model settings")
        
        # Get updated settings
        settings = SettingsService.get_model_settings()
        return ModelSettingsResponse(**settings)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating model settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update model settings: {str(e)}")


@app.post("/settings/model/test", response_model=ValidateApiKeyResponse)
async def test_saved_model_config(admin: dict = Depends(require_admin)):
    """Test saved model configuration using stored API key (admin-only)."""
    try:
        result = SettingsService.test_saved_configuration()
        return ValidateApiKeyResponse(**result)
    except Exception as e:
        logger.error(f"Error testing saved model configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to test saved configuration: {str(e)}")


@app.post("/settings/model/reload")
async def reload_agent(admin: dict = Depends(require_admin)):
    """Reload agent with new settings (admin-only)."""
    global agent, runner
    
    try:
        logger.info("Reloading agent with new settings...")
        agent = create_sre_agent()
        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=session_service,
        )
        logger.info("Agent reloaded successfully")
        return {"message": "Agent reloaded successfully", "tools_count": len(agent.tools) if agent.tools else 0}
    except Exception as e:
        logger.error(f"Error reloading agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reload agent: {str(e)}")


# Security scan endpoints
class SecurityScanRequest(BaseModel):
    cluster_id: Optional[str] = None  # None = scan all clusters
    namespaces: Optional[List[str]] = None


class SecurityScanResponse(BaseModel):
    scan_id: str
    cluster_id: str
    status: str
    timestamp: str
    message: Optional[str] = None


@app.post("/security/scan", response_model=SecurityScanResponse)
async def trigger_security_scan(request: SecurityScanRequest, admin: dict = Depends(require_admin)):
        """Trigger a security scan for one or all clusters."""
        if not security_scanner:
            raise HTTPException(status_code=503, detail="Security scanner not initialized")
        
        try:
            if request.cluster_id:
                # Scan single cluster
                result = await security_scanner.scan_cluster_async(
                    cluster_id=request.cluster_id,
                    namespaces=request.namespaces,
                )
                return SecurityScanResponse(
                    scan_id=result["scan_id"],
                    cluster_id=result["cluster_id"],
                    status=result["status"],
                    timestamp=result["timestamp"],
                    message="Security scan completed"
                )
            else:
                # Scan all clusters
                results = await security_scanner.scan_all_clusters_async(
                    namespaces=request.namespaces,
                )
                return SecurityScanResponse(
                    scan_id="all-clusters",
                    cluster_id="all",
                    status="completed",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    message=f"Security scan completed for {len(results)} clusters"
                )
        except Exception as e:
            logger.error(f"Security scan failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Security scan failed: {e}")

@app.get("/security/scans/{cluster_id}")
async def get_security_scans(cluster_id: str, limit: Optional[int] = 10, admin: dict = Depends(require_admin)):
        """Get security scan results for a cluster."""
        if not security_scanner:
            raise HTTPException(status_code=503, detail="Security scanner not initialized")
        
        try:
            results = await security_scanner.scan_storage.get_scan_results(
                cluster_id=cluster_id,
                limit=limit,
            )
            return {"cluster_id": cluster_id, "scans": results}
        except Exception as e:
            logger.error(f"Failed to get scan results: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get scan results: {e}")

@app.get("/security/scans/{cluster_id}/latest")
async def get_latest_scan(cluster_id: str):
        """Get the latest security scan result for a cluster."""
        if not security_scanner:
            raise HTTPException(status_code=503, detail="Security scanner not initialized")
        
        try:
            result = await security_scanner.scan_storage.get_latest_scan(cluster_id)
            if not result:
                raise HTTPException(status_code=404, detail="No scan results found")
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get latest scan: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get latest scan: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)

