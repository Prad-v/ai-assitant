"""ADK Agent for Kubernetes troubleshooting."""

import os
from google.adk.agents import Agent
from typing import List, Optional, Union

# Import ADK's native McpToolset as per ADK documentation:
# https://google.github.io/adk-docs/tools-custom/mcp-tools/
try:
    from google.adk.tools import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams, StreamableHTTPConnectionParams
except ImportError:
    McpToolset = None
    SseConnectionParams = None
    StreamableHTTPConnectionParams = None

# Import LiteLLM for OpenAI support
try:
    from google.adk.models.lite_llm import LiteLlm
except ImportError:
    LiteLlm = None

# Get model configuration from environment
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "gemini")  # gemini or openai
MODEL_NAME = os.getenv("MODEL_NAME", None)

# Determine model based on provider
if MODEL_NAME:
    MODEL = MODEL_NAME
elif MODEL_PROVIDER == "openai":
    MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
else:
    MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

APP_NAME = os.getenv("APP_NAME", "sreagent")
AGENT_NAME = os.getenv("AGENT_NAME", "k8s_troubleshooting_agent")

# MCP server configuration
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "kubernetes-mcp-server")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8080"))
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "http")  # stdio or http


def create_sre_agent() -> Agent:
    """
    Create the SRE troubleshooting agent with MCP tools integration.
    
    Uses ADK's native McpToolset directly as per ADK documentation:
    https://google.github.io/adk-docs/tools-custom/mcp-tools/#example-1-file-system-mcp-server
    
    Returns:
        Configured ADK Agent instance
    """
    tools = []
    
    # Add MCP tools using ADK's native McpToolset directly
    # This follows the pattern from ADK documentation
    if McpToolset is not None:
        try:
            if MCP_TRANSPORT == "http":
                # Use SSE connection for kubernetes-mcp-server
                sse_url = f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}/sse"
                
                # Try SseConnectionParams first (for SSE servers like kubernetes-mcp-server)
                if SseConnectionParams is not None:
                    try:
                        mcp_toolset = McpToolset(
                            connection_params=SseConnectionParams(url=sse_url)
                        )
                        tools.append(mcp_toolset)
                    except Exception:
                        # Fallback to StreamableHTTPConnectionParams
                        if StreamableHTTPConnectionParams is not None:
                            mcp_toolset = McpToolset(
                                connection_params=StreamableHTTPConnectionParams(url=sse_url)
                            )
                            tools.append(mcp_toolset)
                elif StreamableHTTPConnectionParams is not None:
                    mcp_toolset = McpToolset(
                        connection_params=StreamableHTTPConnectionParams(url=sse_url)
                    )
                    tools.append(mcp_toolset)
            elif MCP_TRANSPORT == "stdio":
                # Use stdio transport
                from mcp import StdioServerParameters
                try:
                    from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
                    mcp_toolset = McpToolset(
                        connection_params=StdioConnectionParams(
                            server_params=StdioServerParameters(
                                command="kubernetes-mcp-server",
                                args=[],
                            )
                        )
                    )
                    tools.append(mcp_toolset)
                except ImportError:
                    # Fallback to StdioServerParameters directly
                    mcp_toolset = McpToolset(
                        connection_params=StdioServerParameters(
                            command="kubernetes-mcp-server",
                            args=[],
                        )
                    )
                    tools.append(mcp_toolset)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to create McpToolset: {e}")
    
    # Configure model based on provider
    # For OpenAI: Use LiteLLM wrapper with "openai/gpt-4" format
    # For Gemini: Use model name directly (native ADK support)
    if MODEL_PROVIDER == "openai" and LiteLlm is not None:
        # Use LiteLLM wrapper for OpenAI models
        # Format: "openai/gpt-4", "openai/gpt-4-turbo", etc.
        model_name = f"openai/{MODEL}" if not MODEL.startswith("openai/") else MODEL
        model = LiteLlm(model=model_name)
    else:
        # Use model name directly for Gemini (native ADK support)
        model_name = MODEL
        model = model_name
    
    agent = Agent(
        model=model,
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

