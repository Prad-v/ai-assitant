"""Entry point for ADK web interface."""

import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.sreagent.agent import create_sre_agent
from backend.services.sreagent.mcp_client import create_mcp_tools
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize agent for ADK web interface
async def init_agent():
    """Initialize agent with MCP tools."""
    try:
        mcp_tools = await create_mcp_tools()
        agent = create_sre_agent(mcp_tools=mcp_tools if mcp_tools else [])
        return agent
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        return create_sre_agent(mcp_tools=[])

# Create agent synchronously for ADK
root_agent = asyncio.run(init_agent())

