# ADK Web Interface Guide

## Overview

The SRE Agent uses Google ADK's built-in web interface for interactive chat with the agent. This provides a user-friendly UI for testing and interacting with the Kubernetes troubleshooting agent.

## Accessing the Web Interface

### Local Development

When running locally with Docker Compose:

```bash
docker compose up -d
# Access at http://localhost:8000
```

### Kubernetes Deployment

#### Port Forward

```bash
kubectl port-forward -n sreagent svc/sreagent 8000:80
# Access at http://localhost:8000
```

#### Via Ingress

If ingress is enabled in the Helm chart:

```bash
# Add to /etc/hosts (or configure DNS)
echo "127.0.0.1 sreagent.local" | sudo tee -a /etc/hosts

# Access at http://sreagent.local
```

## Using the Web Interface

1. **Open the Web Interface**: Navigate to `http://localhost:8000` (or your configured host)

2. **Select Agent**: In the upper left corner, select the agent (`k8s_troubleshooting_agent`)

3. **Start Chatting**: Type your Kubernetes troubleshooting questions in the chat interface

4. **Example Queries**:
   - "List all pods in the default namespace"
   - "Why is my pod in CrashLoopBackOff?"
   - "Show me the logs for pod my-app-123"
   - "Check the health of all deployments"

## Features

- **Interactive Chat**: Real-time conversation with the agent
- **Session Management**: Maintains conversation context
- **Tool Integration**: Agent can use MCP tools from kubernetes-mcp-server
- **Streaming Responses**: See responses as they're generated

## Configuration

The web interface is configured via environment variables:

- `APP_NAME`: Application name (default: sreagent)
- `GEMINI_MODEL`: Gemini model to use (default: gemini-2.0-flash)
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)

## Troubleshooting

### Web Interface Not Loading

1. Check pod status:
   ```bash
   kubectl get pods -n sreagent
   ```

2. Check logs:
   ```bash
   kubectl logs -n sreagent deployment/sreagent
   ```

3. Verify service:
   ```bash
   kubectl get svc -n sreagent
   ```

### Agent Not Responding

1. Check agent initialization in logs:
   ```bash
   kubectl logs -n sreagent deployment/sreagent | grep -i "agent\|mcp"
   ```

2. Verify MCP server connection:
   ```bash
   kubectl get pods -n sreagent | grep mcp-server
   ```

## References

- [ADK Web Interface Documentation](https://google.github.io/adk-docs/get-started/python/#run-with-web-interface)
- [ADK Documentation](https://google.github.io/adk-docs/)

