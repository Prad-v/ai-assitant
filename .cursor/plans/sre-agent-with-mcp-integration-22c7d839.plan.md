<!-- 22c7d839-441e-417c-bbe7-bc89ebb9d273 858f2023-2491-4529-88f5-1ada43723be5 -->
# SRE Agent with Kubernetes MCP Server Integration

## Overview

Build a Kubernetes troubleshooting chat agent using Google ADK that integrates with kubernetes-mcp-server via MCP protocol. Package everything in Docker, create a Helm chart, and deploy to Kubernetes with validation.

## Implementation Plan

### 1. Project Structure Setup

- Create backend service structure: `backend/services/sreagent/`
- Set up Python package structure with ADK agent
- Create requirements.txt with ADK and MCP dependencies
- Add setup.py for package installation

### 2. ADK Agent Implementation

- **File**: `backend/services/sreagent/agent.py`
- Create K8s troubleshooting agent with ADK
- Configure agent to use MCP tools from kubernetes-mcp-server
- Set up agent with appropriate model (gemini-2.0-flash)
- Add instructions for K8s troubleshooting tasks

- **File**: `backend/services/sreagent/server.py`
- Create FastAPI/Flask web server exposing agent API
- Add REST endpoints for chat interactions
- Integrate ADK Runner and SessionService
- Add health check endpoints

### 3. MCP Integration

- **File**: `backend/services/sreagent/mcp_client.py`
- Create MCP client to connect to kubernetes-mcp-server
- Configure MCP transport (stdio or HTTP)
- Register MCP tools with ADK agent
- Handle MCP protocol communication

### 4. Docker Configuration

- **File**: `Dockerfile`
- Multi-stage build for Python application
- Install ADK dependencies
- Copy application code
- Set up entrypoint for agent server

- **File**: `docker-compose.yml`
- Local development setup
- Include sreagent service
- Include kubernetes-mcp-server service (for local testing)
- Configure networking between services

### 5. Helm Chart Structure

- **Directory**: `helm/sreagent/`
- Create main Helm chart for sreagent
- **File**: `Chart.yaml` - Define chart metadata and dependencies
- **File**: `values.yaml` - Default configuration values
- **File**: `values-dev.yaml` - Development environment values
- **File**: `values-prod.yaml` - Production environment values

- **Subchart Integration**:
- Add kubernetes-mcp-server as Helm dependency in Chart.yaml
- Configure subchart values in values.yaml
- Set up service discovery between sreagent and MCP server

- **Templates**:
- `templates/deployment.yaml` - Main application deployment
- `templates/service.yaml` - Service for web interface
- `templates/configmap.yaml` - Configuration management
- `templates/secret.yaml` - Secrets for credentials
- `templates/ingress.yaml` - Ingress for web access (optional)

### 6. Kubernetes Deployment Configuration

- Configure RBAC for K8s API access
- Set up service accounts with appropriate permissions
- Configure MCP server connection (service name, port)
- Add resource limits and requests
- Configure health checks and probes

### 7. Validation and Testing

- **Directory**: `tests/`
- **File**: `tests/test_mcp_tools.py` - Validate MCP tools availability
- **File**: `tests/test_agent_integration.py` - Test agent-MCP integration
- **File**: `tests/test_deployment.py` - Test K8s deployment
- Create test scripts to validate:
- MCP server connectivity
- Available MCP tools (kubectl, helm, kiali operations)
- Agent can invoke MCP tools
- Web interface endpoints

### 8. Documentation

- **File**: `docs/sreagent-setup.md` - Setup and deployment guide
- **File**: `docs/mcp-integration.md` - MCP integration details
- **File**: `docs/api-reference.md` - API endpoint documentation
- Update main README with sreagent information

### 9. CI/CD Integration

- Update CI pipeline to:
- Build Docker image
- Run tests
- Bump Helm chart version on successful commit
- Update image tags in values.yaml

## Key Files to Create/Modify

**Backend Service:**

- `backend/services/sreagent/agent.py` - ADK agent definition
- `backend/services/sreagent/server.py` - Web API server
- `backend/services/sreagent/mcp_client.py` - MCP client integration
- `backend/services/sreagent/__init__.py` - Package initialization
- `backend/services/sreagent/requirements.txt` - Python dependencies

**Docker & Deployment:**

- `Dockerfile` - Container image definition
- `docker-compose.yml` - Local development setup
- `.dockerignore` - Docker build exclusions

**Helm Chart:**

- `helm/sreagent/Chart.yaml` - Chart definition with dependencies
- `helm/sreagent/values.yaml` - Default values
- `helm/sreagent/values-dev.yaml` - Dev environment
- `helm/sreagent/values-prod.yaml` - Prod environment
- `helm/sreagent/templates/*.yaml` - K8s manifests

**Testing:**

- `tests/test_mcp_tools.py` - MCP validation tests
- `tests/test_agent_integration.py` - Integration tests
- `tests/test_deployment.py` - Deployment validation

**Documentation:**

- `docs/sreagent-setup.md`
- `docs/mcp-integration.md`
- `docs/api-reference.md`

## Dependencies

- Google ADK Python SDK
- kubernetes-mcp-server (as Helm subchart)
- MCP Python SDK for client integration
- FastAPI/Flask for web interface
- Kubernetes Python client (for direct K8s operations if needed)

### To-dos

- [ ] Create backend/services/sreagent directory structure and Python package files
- [ ] Create ADK agent with K8s troubleshooting instructions and model configuration
- [ ] Build FastAPI web server with REST endpoints for agent interactions
- [ ] Implement MCP client to connect to kubernetes-mcp-server and register tools with ADK agent
- [ ] Create Dockerfile for containerizing the sreagent application
- [ ] Set up docker-compose.yml for local development and testing
- [ ] Create Helm chart structure with Chart.yaml, values files, and K8s templates
- [ ] Add kubernetes-mcp-server as Helm dependency and configure subchart values
- [ ] Create deployment, service, configmap, and RBAC manifests in Helm templates
- [ ] Create test scripts to validate MCP tools availability and agent integration
- [ ] Create documentation for setup, MCP integration, and API reference