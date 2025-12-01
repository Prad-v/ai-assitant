"""Agent definition for ADK web interface."""

import os
import sys
import asyncio
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.services.sreagent.agent import create_sre_agent
from backend.services.sreagent.mcp_client import create_mcp_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize agent
async def _init_agent():
    """Initialize agent with MCP tools."""
    try:
        model_provider = os.getenv("MODEL_PROVIDER", "gemini")
        logger.info(f"Initializing SRE Agent with {model_provider} model and MCP tools...")
        mcp_tools = await create_mcp_tools()
        logger.info(f"Found {len(mcp_tools)} MCP tools")
        agent = create_sre_agent(mcp_tools=mcp_tools if mcp_tools else [])
        return agent
    except Exception as e:
        logger.error(f"Failed to initialize agent with MCP tools: {e}")
        logger.info("Initializing agent without MCP tools...")
        return create_sre_agent(mcp_tools=[])

# Create root_agent for ADK web interface
root_agent = asyncio.run(_init_agent())

