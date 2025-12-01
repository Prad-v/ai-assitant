# SRE Agent Setup and Deployment Guide

## Overview

The SRE Agent is a Kubernetes troubleshooting chat agent built with Google ADK that integrates with kubernetes-mcp-server via the Model Context Protocol (MCP). It provides an intelligent interface for diagnosing and resolving Kubernetes cluster issues.

## Prerequisites

- Kubernetes cluster (1.24+)
- Helm 3.8+
- kubectl configured to access your cluster
- Docker (for local development)
- Google Cloud credentials (for Gemini API access)

## Local Development Setup

### 1. Clone and Setup

```bash
# Create virtual environment
make venv
source venv/bin/activate

# Install dependencies
make install
```

### 2. Configure Environment

Create a `.env` file:

```bash
APP_NAME=sreagent
GEMINI_MODEL=gemini-2.0-flash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
MCP_SERVER_HOST=kubernetes-mcp-server
MCP_SERVER_PORT=8080
MCP_TRANSPORT=stdio
```

### 3. Run with Docker Compose

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f sreagent

# Stop services
docker compose down
```

### 4. Test the Agent

```bash
# Health check
curl http://localhost:8000/health

# Chat with agent
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "List all pods in default namespace",
    "user_id": "test_user"
  }'
```

## Kubernetes Deployment

### 1. Build Docker Image

```bash
# Build image
docker build -t sreagent:0.1.0 .

# Tag for registry
docker tag sreagent:0.1.0 your-registry/sreagent:0.1.0

# Push to registry
docker push your-registry/sreagent:0.1.0
```

### 2. Update Helm Chart Values

Edit `helm/sreagent/values.yaml` or use environment-specific files:

```bash
# For development
helm install sreagent ./helm/sreagent -f helm/sreagent/values-dev.yaml

# For production
helm install sreagent ./helm/sreagent -f helm/sreagent/values-prod.yaml
```

### 3. Install Helm Dependencies

```bash
cd helm/sreagent
helm dependency update
cd ../..
```

### 4. Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace sreagent

# Install chart
helm install sreagent ./helm/sreagent \
  --namespace sreagent \
  --set image.repository=your-registry/sreagent \
  --set image.tag=0.1.0

# Check deployment
kubectl get pods -n sreagent
kubectl get svc -n sreagent
```

### 5. Access the Agent

```bash
# Port forward to local machine
kubectl port-forward -n sreagent svc/sreagent 8000:80

# Or access via ingress (if enabled)
curl http://sreagent.example.com/health
```

## Configuration

### Environment Variables

- `APP_NAME`: Application name (default: sreagent)
- `GEMINI_MODEL`: Gemini model to use (default: gemini-2.0-flash)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `MCP_SERVER_HOST`: MCP server hostname (default: kubernetes-mcp-server)
- `MCP_SERVER_PORT`: MCP server port (default: 8080)
- `MCP_TRANSPORT`: MCP transport type (stdio or http)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to Google credentials JSON

### Helm Values

Key configuration options in `values.yaml`:

- `replicaCount`: Number of replicas
- `image.repository`: Docker image repository
- `image.tag`: Docker image tag
- `resources`: CPU and memory limits/requests
- `ingress.enabled`: Enable ingress
- `autoscaling.enabled`: Enable horizontal pod autoscaling

## Troubleshooting

### Agent Not Responding

1. Check pod status:
   ```bash
   kubectl get pods -n sreagent
   kubectl describe pod <pod-name> -n sreagent
   ```

2. Check logs:
   ```bash
   kubectl logs -n sreagent deployment/sreagent
   ```

3. Verify health endpoint:
   ```bash
   kubectl exec -n sreagent deployment/sreagent -- curl localhost:8000/health
   ```

### MCP Connection Issues

1. Verify MCP server is running:
   ```bash
   kubectl get pods -l app=kubernetes-mcp-server
   ```

2. Check MCP server logs:
   ```bash
   kubectl logs -l app=kubernetes-mcp-server
   ```

3. Verify service connectivity:
   ```bash
   kubectl get svc kubernetes-mcp-server
   ```

### Authentication Issues

1. Verify Google credentials:
   ```bash
   kubectl get secret google-credentials -n sreagent
   ```

2. Check service account:
   ```bash
   kubectl get sa sreagent -n sreagent
   ```

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_mcp_tools.py -v
pytest tests/test_agent_integration.py -v
pytest tests/test_deployment.py -v
```

## Uninstallation

```bash
# Remove Helm release
helm uninstall sreagent -n sreagent

# Remove namespace (optional)
kubectl delete namespace sreagent
```

## Next Steps

- See [MCP Integration Guide](mcp-integration.md) for details on MCP tools
- See [API Reference](api-reference.md) for API documentation
- Review [Troubleshooting](#troubleshooting) section for common issues

