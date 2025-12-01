"""FastAPI web server for SRE Agent."""

import os
import logging
import asyncio
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import create_sre_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
APP_NAME = os.getenv("APP_NAME", "sreagent")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

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


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"
    session_id: Optional[str] = None


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
    global session_service, agent, runner
    
    logger.info("Initializing SRE Agent...")
    
    try:
        # Initialize session service
        session_service = InMemorySessionService()
        
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
async def chat(request: ChatRequest):
    """Chat endpoint for interacting with the agent."""
    if not agent or not runner:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Get or create session
        session_id = request.session_id
        if not session_id:
            session_id = f"session_{request.user_id}"
        
        # Ensure session exists before running agent
        # The Runner expects the session to already exist, so we must create it first
        try:
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=request.user_id,
                session_id=session_id,
            )
            logger.info(f"Using existing session: {session_id}")
        except Exception as e:
            # Create new session if it doesn't exist
            logger.info(f"Creating new session: {session_id} (error: {e})")
            try:
                session = await session_service.create_session(
                    app_name=APP_NAME,
                    user_id=request.user_id,
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
                user_id=request.user_id,
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
        logger.info(f"Running agent for session: {session_id}, user: {request.user_id}")
        try:
            # Use run_async instead of run to properly handle async session operations
            events = []
            async for event in runner.run_async(
                user_id=request.user_id,
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
                        user_id=request.user_id,
                        session_id=session_id,
                    )
                    logger.info(f"Session recreated, retrying agent run...")
                    events = []
                    async for event in runner.run_async(
                        user_id=request.user_id,
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
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)

