"""Entry point for ADK web interface."""

import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.sreagent.agent import create_sre_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize agent for ADK web interface
# MCP tools are now handled internally in create_sre_agent()
logger.info("Initializing SRE Agent for ADK web interface...")
root_agent = create_sre_agent()
logger.info("SRE Agent initialized successfully")
