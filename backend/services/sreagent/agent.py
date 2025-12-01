"""ADK Agent for Kubernetes troubleshooting."""

import os
from google.adk.agents import Agent
from typing import List, Optional

# GoogleTool may not be directly importable - will handle in mcp_client
try:
    from google.adk.tools import GoogleTool
except ImportError:
    # Fallback if GoogleTool is not available
    GoogleTool = None

# Get model from environment or use default
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
APP_NAME = os.getenv("APP_NAME", "sreagent")
AGENT_NAME = os.getenv("AGENT_NAME", "k8s_troubleshooting_agent")


def create_sre_agent(mcp_tools: Optional[List] = None) -> Agent:
    """
    Create the SRE troubleshooting agent with MCP tools integration.
    
    Args:
        mcp_tools: List of MCP tools to register with the agent
        
    Returns:
        Configured ADK Agent instance
    """
    tools = []
    
    # Add MCP tools if provided
    if mcp_tools:
        tools.extend(mcp_tools)
    
    agent = Agent(
        model=MODEL,
        name=AGENT_NAME,
        description=(
            "A specialized Kubernetes troubleshooting agent that helps diagnose "
            "and resolve issues in Kubernetes clusters. Can execute kubectl commands, "
            "analyze logs, inspect resources, and perform Helm operations."
        ),
        instruction="""\
You are an expert Kubernetes Site Reliability Engineer (SRE) assistant. Your role is to help 
users troubleshoot and resolve issues in Kubernetes clusters.

Key capabilities:
1. Execute kubectl commands to inspect cluster state
2. Analyze pod logs and events
3. Check resource health and status
4. Perform Helm chart operations
5. Diagnose common K8s issues (pod failures, networking, resource constraints)
6. Provide actionable recommendations

When troubleshooting:
- Start by gathering information about the affected resources
- Check pod status, events, and logs
- Verify resource quotas and limits
- Examine service endpoints and networking
- Look for common patterns (OOMKilled, CrashLoopBackOff, ImagePullBackOff, etc.)

Always explain what you're doing and why. Provide clear, step-by-step guidance.
Use the available tools to gather information before making recommendations.
""",
        tools=tools if tools else [],
    )
    
    return agent

