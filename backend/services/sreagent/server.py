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
from .mcp_client import create_mcp_tools

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
        
        # Create MCP tools
        logger.info("Connecting to MCP server...")
        mcp_tools = await create_mcp_tools()
        logger.info(f"Connected to MCP server. Found {len(mcp_tools)} tools.")
        
        # Create agent with MCP tools
        agent = create_sre_agent(mcp_tools=mcp_tools if mcp_tools else None)
        
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
        agent = create_sre_agent(mcp_tools=None)
        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=InMemorySessionService(),
        )
        logger.warning("Agent initialized without MCP tools")


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
        
        # Create session if it doesn't exist
        try:
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=request.user_id,
                session_id=session_id,
            )
        except Exception:
            # Create new session
            session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=request.user_id,
                session_id=session_id,
            )
        
        # Create user message
        content = types.Content(
            role="user",
            parts=[types.Part(text=request.message)],
        )
        
        # Run agent
        events = runner.run(
            user_id=request.user_id,
            session_id=session_id,
            new_message=content,
        )
        
        # Collect response
        response_text = ""
        for event in events:
            if event.is_final_response():
                response_text = event.content.parts[0].text
                break
        
        if not response_text:
            response_text = "I received your message but couldn't generate a response."
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
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

