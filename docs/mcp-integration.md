# MCP Integration Guide

## Overview

The SRE Agent integrates with kubernetes-mcp-server using the Model Context Protocol (MCP) to provide Kubernetes troubleshooting capabilities. This document explains how the integration works and how to configure it.

## What is MCP?

The Model Context Protocol (MCP) is a protocol that enables AI agents to interact with external tools and data sources. The kubernetes-mcp-server exposes Kubernetes operations as MCP tools that the agent can invoke.

## Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│             │         │                  │         │                     │
│ SRE Agent   │◄───────►│  MCP Client      │◄───────►│ kubernetes-mcp-     │
│  (ADK)      │         │  (mcp_client.py) │         │ server              │
│             │         │                  │         │                     │
└─────────────┘         └──────────────────┘         └─────────────────────┘
```

## Available MCP Tools

The kubernetes-mcp-server provides the following categories of tools:

### Kubectl Operations

- `kubectl_get`: Get Kubernetes resources
- `kubectl_describe`: Describe Kubernetes resources
- `kubectl_logs`: Get pod logs
- `kubectl_exec`: Execute commands in pods
- `kubectl_apply`: Apply Kubernetes manifests
- `kubectl_delete`: Delete Kubernetes resources

### Helm Operations

- `helm_install`: Install Helm charts
- `helm_list`: List Helm releases
- `helm_uninstall`: Uninstall Helm releases

### Kiali Operations (if Istio is installed)

- `kiali_get_mesh_graph`: Get service mesh topology
- `kiali_get_metrics`: Get service metrics
- `kiali_get_traces`: Get distributed traces
- `kiali_manage_istio_config`: Manage Istio configuration

## Configuration

### Transport Types

The MCP client supports two transport types:

1. **stdio** (default): Direct subprocess communication
   - Used when MCP server runs in the same container
   - Configured via `MCP_TRANSPORT=stdio`

2. **http**: HTTP-based communication
   - Used when MCP server is a separate service
   - Configured via `MCP_TRANSPORT=http`
   - Requires `MCP_SERVER_HOST` and `MCP_SERVER_PORT`

### Environment Variables

```bash
MCP_SERVER_HOST=kubernetes-mcp-server  # Service name or hostname
MCP_SERVER_PORT=8080                   # Service port
MCP_TRANSPORT=stdio                    # Transport type
```

### Kubernetes Configuration

In the Helm chart, MCP server connection is configured via values:

```yaml
mcp:
  serverHost: "kubernetes-mcp-server"
  serverPort: 8080
  transport: "stdio"
```

## How It Works

### 1. Agent Initialization

When the SRE Agent starts:

1. Creates MCP client connection
2. Connects to kubernetes-mcp-server
3. Lists available MCP tools
4. Registers tools with ADK agent
5. Agent is ready to use tools

### 2. Tool Invocation

When a user asks a question:

1. Agent analyzes the request
2. Determines which MCP tools to use
3. Invokes tools via MCP protocol
4. Receives results from kubernetes-mcp-server
5. Formats response for user

### Example Flow

```
User: "List all pods in default namespace"

Agent → MCP Client → kubernetes-mcp-server
                    ↓
                    kubectl get pods -n default
                    ↓
Agent ← MCP Client ← [pod list results]
                    ↓
Agent: "Here are the pods in default namespace: ..."
```

## Troubleshooting MCP Integration

### Check MCP Server Status

```bash
# Check if MCP server pod is running
kubectl get pods -l app=kubernetes-mcp-server

# Check MCP server logs
kubectl logs -l app=kubernetes-mcp-server
```

### Verify Service Connectivity

```bash
# Check service
kubectl get svc kubernetes-mcp-server

# Test connectivity from agent pod
kubectl exec -n sreagent deployment/sreagent -- \
  curl http://kubernetes-mcp-server:8080/health
```

### Check Agent MCP Connection

```bash
# Check health endpoint
curl http://localhost:8000/health

# Response should include:
# {
#   "status": "healthy",
#   "agent_ready": true,
#   "mcp_connected": true
# }
```

### Common Issues

1. **MCP server not found**
   - Verify service name matches `MCP_SERVER_HOST`
   - Check service is in the same namespace

2. **Connection timeout**
   - Verify network policies allow communication
   - Check service port matches configuration

3. **Tools not available**
   - Check MCP server logs for errors
   - Verify RBAC permissions for MCP server

## Testing MCP Tools

### Using MCP Inspector

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Port forward MCP server
kubectl port-forward -n sreagent svc/kubernetes-mcp-server 8080:8080

# Run inspector
npx @modelcontextprotocol/inspector
```

### Manual Tool Testing

```bash
# Test kubectl tool via agent
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Get all pods in default namespace",
    "user_id": "test"
  }'
```

## Security Considerations

1. **RBAC**: MCP server needs appropriate Kubernetes permissions
2. **Network Policies**: Restrict network access to MCP server
3. **Service Account**: Use dedicated service account for MCP server
4. **Credentials**: Secure Google Cloud credentials

## References

- [kubernetes-mcp-server GitHub](https://github.com/containers/kubernetes-mcp-server)
- [MCP Protocol Documentation](https://modelcontextprotocol.io)
- [ADK Tools Documentation](https://google.github.io/adk-docs/tools/built-in-tools/)

