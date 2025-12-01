"""Agent definition for ADK web interface.

This follows the ADK documentation pattern:
https://google.github.io/adk-docs/tools-custom/mcp-tools/#example-1-file-system-mcp-server
"""

import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.services.sreagent.agent import create_sre_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize agent - McpToolset is created directly in create_sre_agent()
# This follows the ADK documentation pattern where McpToolset is defined
# directly in the agent definition, not in a separate client file
model_provider = os.getenv("MODEL_PROVIDER", "openai")
logger.info(f"Initializing SRE Agent with {model_provider} model...")

# Create the agent - McpToolset will be initialized synchronously
# ADK handles the async connection internally when tools are used
root_agent = create_sre_agent()
logger.info("SRE Agent initialized with MCP tools")

