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
# Standardized through LiteLLM - supports all providers
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "gemini")  # gemini, openai, anthropic, etc.
MODEL_NAME = os.getenv("MODEL_NAME", None)

# API keys from environment (should be set from K8s secrets)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)  # For Gemini via LiteLLM

# Token optimization settings
MAX_TOKENS = os.getenv("MAX_TOKENS", None)
TEMPERATURE = os.getenv("TEMPERATURE", None)

# Determine model based on provider
# LiteLLM format: "provider/model-name" (e.g., "openai/gpt-4", "gemini/gemini-2.0-flash")
if MODEL_NAME:
    # If MODEL_NAME already includes provider prefix, use as-is
    # Otherwise, add provider prefix
    if "/" in MODEL_NAME:
        MODEL = MODEL_NAME
    else:
        MODEL = f"{MODEL_PROVIDER}/{MODEL_NAME}"
elif MODEL_PROVIDER == "openai":
    model_name = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    MODEL = f"openai/{model_name}"
elif MODEL_PROVIDER == "gemini":
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    MODEL = f"gemini/{model_name}"
else:
    # For other providers, use provider/model format
    model_name = os.getenv("MODEL_NAME", "default")
    MODEL = f"{MODEL_PROVIDER}/{model_name}"

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
    
    # Configure model using LiteLLM (standardized for all providers)
    # LiteLLM supports: openai, gemini, anthropic, etc.
    # Format: "provider/model-name" (e.g., "openai/gpt-4", "gemini/gemini-2.0-flash")
    if LiteLlm is None:
        import logging
        logger = logging.getLogger(__name__)
        logger.error("LiteLLM is not available. Please ensure litellm is installed.")
        raise ImportError("LiteLLM is required for model configuration")
    
    # Build LiteLLM configuration with token optimization
    lite_llm_kwargs = {"model": MODEL}
    
    # Set API keys if provided (from K8s secrets)
    if OPENAI_API_KEY:
        lite_llm_kwargs["api_key"] = OPENAI_API_KEY
    elif GEMINI_API_KEY:
        lite_llm_kwargs["api_key"] = GEMINI_API_KEY
    
    # Add token optimization settings
    if MAX_TOKENS:
        try:
            lite_llm_kwargs["max_tokens"] = int(MAX_TOKENS)
        except ValueError:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid MAX_TOKENS value: {MAX_TOKENS}")
    
    if TEMPERATURE:
        try:
            lite_llm_kwargs["temperature"] = float(TEMPERATURE)
        except ValueError:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid TEMPERATURE value: {TEMPERATURE}")
    
    model = LiteLlm(**lite_llm_kwargs)
    
    agent = Agent(
        model=model,
        name=AGENT_NAME,
        description=(
            "A specialized Kubernetes troubleshooting agent that helps diagnose "
            "and resolve issues in Kubernetes clusters. Can execute kubectl commands, "
            "analyze logs, inspect resources, and perform Helm operations."
        ),
        instruction="""\
You are a Kubernetes SRE assistant. Diagnose and resolve K8s issues efficiently.

EFFICIENCY RULES (CRITICAL for token optimization):
- Use specific queries: pods_get <name> -n <namespace> (not pods_list all)
- Limit log retrieval: pods_logs <name> --tail=50 (max 100 lines)
- Query targeted resources, avoid listing all namespaces
- Use field selectors for events: events_list with fieldSelector
- Cache information: don't repeat identical queries
- Request only necessary fields, avoid full resource dumps

Troubleshooting flow:
1. pods_get <specific-name> -n <namespace> (targeted pod status)
2. events_list with fieldSelector (targeted events, not all)
3. pods_logs <name> --tail=50 (limited logs, not full history)
4. resources_get only if needed (specific resource, not list all)

Common issues: OOMKilled, CrashLoopBackOff, ImagePullBackOff, CreateContainerConfigError, ImagePullBackOff.

Provide concise root cause analysis. Be selective with data requests to minimize token usage.
""",
        tools=tools if tools else [],
    )
    
    return agent

