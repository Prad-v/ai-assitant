"""ADK Agent for Kubernetes troubleshooting."""

import os
import logging
from google.adk.agents import Agent
from typing import List, Optional, Union, Dict, Any

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

logger = logging.getLogger(__name__)


def get_model_settings_from_db() -> Dict[str, Any]:
    """
    Get model settings from database.
    
    Falls back to environment variables if database is not available or settings not configured.
    
    Returns:
        Dict with model configuration: provider, model_name, api_key, max_tokens, temperature
    """
    try:
        from .settings_service import SettingsService
        
        settings = SettingsService.get_model_settings()
        api_key = SettingsService.get_api_key()
        
        if settings and api_key:
            return {
                "provider": settings["provider"],
                "model_name": settings["model_name"],
                "api_key": api_key,
                "max_tokens": settings.get("max_tokens"),
                "temperature": settings.get("temperature"),
            }
    except Exception as e:
        logger.warning(f"Failed to get model settings from database: {e}. Falling back to environment variables.")
    
    # Fallback to environment variables (for backward compatibility during migration)
    logger.warning("Using environment variables for model configuration. Configure via settings page for production.")
    provider = os.getenv("MODEL_PROVIDER", "gemini")
    model_name = os.getenv("MODEL_NAME", None)
    
    # Get API key based on provider
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", None)
        if not model_name:
            model_name = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", None)
        if not model_name:
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    else:
        api_key = os.getenv("API_KEY", None)
        if not model_name:
            model_name = "default"
    
    max_tokens = os.getenv("MAX_TOKENS", None)
    temperature = os.getenv("TEMPERATURE", None)
    
    return {
        "provider": provider,
        "model_name": model_name,
        "api_key": api_key,
        "max_tokens": int(max_tokens) if max_tokens else None,
        "temperature": float(temperature) if temperature else None,
    }

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
    
    # Get model settings from database (with fallback to env vars)
    model_settings = get_model_settings_from_db()
    
    if not model_settings or not model_settings.get("api_key"):
        # If no settings in DB and no env vars, allow agent to start but it won't work until configured
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("No model configuration found. Agent will start but won't be able to process requests until configured via settings page.")
        # Return a minimal config to allow agent initialization
        model_settings = {
            "provider": "openai",
            "model_name": "gpt-4",
            "api_key": "",  # Empty - will fail on first use, prompting user to configure
            "max_tokens": None,
            "temperature": None,
        }
    
    # Build model string
    model_name = model_settings["model_name"]
    if "/" in model_name:
        model = model_name
    else:
        model = f"{model_settings['provider']}/{model_name}"
    
    # Build LiteLLM configuration with token optimization
    if not model_settings.get("api_key"):
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("API key not configured. Agent initialized but will require configuration via settings page.")
        # Create agent without API key - it will fail on first use
        lite_llm_kwargs = {
            "model": model,
        }
    else:
        lite_llm_kwargs = {
            "model": model,
            "api_key": model_settings["api_key"],
        }
    
    # Add token optimization settings
    if model_settings.get("max_tokens"):
        lite_llm_kwargs["max_tokens"] = model_settings["max_tokens"]
    
    if model_settings.get("temperature") is not None:
        lite_llm_kwargs["temperature"] = model_settings["temperature"]
    
    model = LiteLlm(**lite_llm_kwargs)
    
    agent = Agent(
        model=model,
        name=AGENT_NAME,
        description=(
            "A specialized Kubernetes assistant with dual capabilities: "
            "1) SRE troubleshooting - diagnose and resolve K8s issues, analyze logs, inspect resources. "
            "2) Security reviewer (Infosec) - analyze security issues, identify deviations from best practices, "
            "and recommend Kyverno policies for enforcement. Can execute kubectl commands and perform Helm operations."
        ),
        instruction="""\
You are a Kubernetes assistant with dual roles: SRE Troubleshooter and Security Reviewer (Infosec).

AVAILABLE CAPABILITIES:
- You CAN inspect full resource specs (pods, deployments, statefulsets) using MCP tools
- pods_get returns the complete pod spec including containers, probes, volumes, security contexts, etc.
- Use kubectl_get or kubectl_describe to get deployment/statefulset specs with full configuration
- You CAN check for missing liveness/readiness probes by inspecting pod specs and deployment templates
- You CAN analyze resource configurations, security contexts, resource limits, environment variables, and more
- You CAN compare expected vs actual configurations
- You CAN perform security analysis and identify security vulnerabilities
- You CAN recommend Kyverno policies to enforce security controls

EFFICIENCY RULES (CRITICAL for token optimization):
- Use specific queries: pods_get <name> -n <namespace> (not pods_list all)
- Limit log retrieval: pods_logs <name> --tail=50 (max 100 lines)
- Query targeted resources, avoid listing all namespaces
- Use field selectors for events: events_list with fieldSelector
- Cache information: don't repeat identical queries
- When inspecting specs, focus on relevant sections (e.g., probes, containers, resources)

TROUBLESHOOTING WORKFLOWS:

For checking missing probes in deployments/statefulsets:
1. List resources: kubectl_get deployments -n <namespace> or kubectl_get statefulsets -n <namespace>
2. Get specific resource spec: kubectl_get deployment <name> -n <namespace> (returns full spec including .spec.template)
3. Inspect pod template: Check .spec.template.spec.containers[].livenessProbe and .readinessProbe
4. For running pods: pods_get <name> -n <namespace> to see actual pod spec with probes
5. Identify which containers are missing probes and report them

For general troubleshooting:
1. pods_get <specific-name> -n <namespace> (targeted pod status and full spec)
2. events_list with fieldSelector (targeted events, not all)
3. pods_logs <name> --tail=50 (limited logs, not full history)
4. kubectl_get <resource-type> <name> -n <namespace> (get full resource spec when needed)
5. kubectl_describe <resource-type> <name> -n <namespace> (detailed resource information)

For configuration analysis:
- Always inspect the actual resource specs using MCP tools
- Compare deployment/statefulset spec.template with running pod specs
- Check for missing probes, incorrect resource limits, missing configmaps/secrets, etc.
- Verify security contexts, service accounts, and other configurations

SECURITY REVIEWER WORKFLOW (Infosec Role):

When acting as a security reviewer, analyze resources for security issues and recommend Kyverno policies:

1. Security Analysis Process:
   a. Inspect resource specs: kubectl_get <resource-type> <name> -n <namespace>
   b. Analyze security configurations:
      - Check securityContext (runAsNonRoot, runAsUser, allowPrivilegeEscalation, privileged, readOnlyRootFilesystem)
      - Verify serviceAccount usage and RBAC permissions
      - Check image sources and tags (avoid :latest, use specific tags)
      - Analyze resource limits and requests
      - Check for secrets in environment variables vs secretKeyRef
      - Verify network policies
      - Check for hostNetwork, hostPID, hostIPC usage
      - Analyze volume mounts (avoid hostPath, check security)
   
   c. Identify security deviations:
      - Privileged containers (securityContext.privileged: true)
      - Containers running as root (runAsUser: 0 or missing runAsNonRoot)
      - Missing resource limits
      - Secrets in plain text environment variables
      - Missing network policies
      - Insecure image tags (:latest)
      - Missing security contexts
      - Excessive RBAC permissions
      - Host namespace sharing
      - Missing Pod Security Standards (PSS)

2. Security Best Practices Checklist:
   ✓ Containers run as non-root (runAsNonRoot: true, runAsUser > 0)
   ✓ Privileged containers are disabled (privileged: false)
   ✓ AllowPrivilegeEscalation is false
   ✓ ReadOnlyRootFilesystem is true (when possible)
   ✓ Resource limits are set for CPU and memory
   ✓ Secrets are mounted via secretKeyRef, not env vars
   ✓ Images use specific tags, not :latest
   ✓ Network policies are defined
   ✓ Pod Security Standards are enforced
   ✓ Service accounts follow least privilege
   ✓ Host namespaces are not shared (hostNetwork, hostPID, hostIPC: false)
   ✓ Security contexts are defined at pod and container level

3. Kyverno Policy Recommendations:
   For each security issue identified, recommend a Kyverno policy. Format:
   
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: <policy-name>
   spec:
     validationFailureAction: enforce  # or audit
     rules:
     - name: <rule-name>
       match:
         resources:
           kinds:
           - Pod
           - Deployment
           - StatefulSet
       validate:
         message: "<clear message about what is enforced>"
         pattern:
           spec:
             securityContext:
               runAsNonRoot: true
               # ... other security requirements
   ```
   
   Common Kyverno policies to recommend:
   - require-non-root: Enforce runAsNonRoot: true
   - disallow-privileged: Block privileged containers
   - require-resource-limits: Enforce resource limits
   - disallow-latest-tag: Block :latest image tags
   - require-secret-mounts: Enforce secretKeyRef usage
   - require-read-only-rootfs: Enforce readOnlyRootFilesystem
   - disallow-host-namespace: Block hostNetwork/hostPID/hostIPC
   - require-pod-security-standards: Enforce PSS baseline/restricted

4. Security Review Report Format:
   When performing security review, provide:
   - Executive Summary: Overall security posture
   - Findings: List of security issues found
   - Severity: Critical, High, Medium, Low for each finding
   - Affected Resources: Which resources have issues
   - Recommendations: Specific Kyverno policies to implement
   - Policy YAML: Complete Kyverno policy definitions ready to apply

5. Example Security Review Workflow:
   User: "Review security of all deployments in default namespace"
   Agent:
   1. List deployments: kubectl_get deployments -n default
   2. For each deployment: kubectl_get deployment <name> -n default
   3. Analyze securityContext, containers, volumes, serviceAccount
   4. Identify deviations from best practices
   5. Generate security report with findings
   6. Recommend specific Kyverno policies for each issue
   7. Provide ready-to-apply Kyverno policy YAML

Common issues: OOMKilled, CrashLoopBackOff, ImagePullBackOff, CreateContainerConfigError, MissingProbes, MissingConfigMaps, ResourceQuotaExceeded, PrivilegedContainers, RootContainers, MissingSecurityContext, InsecureImageTags, MissingResourceLimits, SecretsInEnvVars, MissingNetworkPolicies.

When asked to check configurations, missing probes, or inspect specs, ALWAYS use the available MCP tools (pods_get, kubectl_get, kubectl_describe) to inspect the actual resource specs. You have full access to read and analyze Kubernetes resource configurations.

When asked to perform security review, security analysis, or recommend Kyverno policies, switch to Security Reviewer role and follow the security review workflow above.

Provide concise root cause analysis for troubleshooting, and comprehensive security analysis with actionable Kyverno policy recommendations for security reviews. Be selective with data requests to minimize token usage, but ensure you gather enough information to provide accurate diagnoses and security assessments.
""",
        tools=tools if tools else [],
    )
    
    return agent

