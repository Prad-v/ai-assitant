# AI Assistant - SRE Agent

A Kubernetes troubleshooting chat agent built with Google ADK that integrates with kubernetes-mcp-server via the Model Context Protocol (MCP).

## Features

- **Intelligent K8s Troubleshooting**: AI-powered assistant for diagnosing Kubernetes cluster issues
- **MCP Integration**: Seamless integration with kubernetes-mcp-server for Kubernetes operations
- **React UI**: Modern React-based frontend for chat interface (separate service)
- **ADK Web Interface**: Built-in web UI for interactive chat with the agent (via `adk web`)
- **REST API**: Programmatic access via FastAPI endpoints
- **Helm Deployment**: Production-ready Helm chart with kubernetes-mcp-server as subchart
- **Docker Support**: Containerized application with Docker Compose for local development

## Quick Start

### Local Development

```bash
# Create virtual environment
make venv
source venv/bin/activate

# Install dependencies
make install

# Run with Docker Compose
docker compose up -d

# Test the agent
curl http://localhost:8000/health

# Access React UI
# Open browser to http://localhost:3000

# Access ADK web interface
# Open browser to http://localhost:8000/dev-ui/
```

### Kubernetes Deployment

```bash
# Build and push Docker image
docker build -t sreagent:0.1.0 .
docker tag sreagent:0.1.0 your-registry/sreagent:0.1.0
docker push your-registry/sreagent:0.1.0

# Install Helm dependencies
cd helm/sreagent
helm dependency update
cd ../..

# Deploy to Kubernetes
helm install sreagent ./helm/sreagent \
  --namespace sreagent \
  --create-namespace \
  --set image.repository=your-registry/sreagent \
  --set image.tag=0.1.0 \
  --set ingress.enabled=true

# Access the web interfaces
# React UI: kubectl port-forward -n sreagent svc/sreagent-frontend 3000:3000
# ADK Web UI: kubectl port-forward -n sreagent svc/sreagent 8000:80
# Or via ingress (if configured): http://sreagent-ui.local (React) or http://sreagent.local (ADK)
```

## Project Structure

```
.
├── frontend/                   # React frontend UI
│   ├── src/                   # React source code
│   ├── public/                 # Static files
│   ├── Dockerfile             # Frontend Docker build
│   └── package.json           # Frontend dependencies
├── backend/
│   └── services/
│       └── sreagent/          # SRE Agent service
│           ├── agent.py       # ADK agent definition
│           ├── server.py      # FastAPI web server
│           ├── mcp_client.py  # MCP client integration
│           └── requirements.txt
├── helm/
│   └── sreagent/              # Helm chart
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
├── tests/                     # Test suite
│   ├── test_mcp_tools.py
│   ├── test_agent_integration.py
│   └── test_deployment.py
├── docs/                      # Documentation
│   ├── sreagent-setup.md
│   ├── mcp-integration.md
│   └── api-reference.md
├── Dockerfile
├── docker-compose.yml
└── Makefile
```

## Documentation

- [Setup Guide](docs/sreagent-setup.md) - Installation and deployment instructions
- [MCP Integration](docs/mcp-integration.md) - MCP protocol integration details
- [API Reference](docs/api-reference.md) - REST API documentation
- [React UI Guide](docs/react-ui-guide.md) - React frontend usage guide
- [ADK Web Interface](docs/adk-web-interface.md) - ADK web UI usage guide
- [Generic API Key Secret](docs/generic-api-key-secret.md) - Generic API key secret configuration
- [OpenAI Configuration](docs/openai-configuration.md) - OpenAI model setup guide
- [Security Reviewer Workflow](docs/security-reviewer-workflow.md) - Security analysis guide

## Testing

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_mcp_tools.py -v
```

## Configuration

Key environment variables:

- `MODEL_PROVIDER`: Model provider - "gemini" or "openai" (default: gemini)
- `MODEL_NAME`: Specific model name (optional, uses provider default if not set)
- `GEMINI_MODEL`: Gemini model to use (default: gemini-2.0-flash)
- `OPENAI_MODEL`: OpenAI model to use (default: gpt-4)
- `OPENAI_API_KEY` or `GEMINI_API_KEY`: API key from generic `model-api-key` secret (set based on `MODEL_PROVIDER`)
- `MCP_SERVER_HOST`: MCP server hostname (default: kubernetes-mcp-server)
- `MCP_SERVER_PORT`: MCP server port (default: 8080)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to Google Cloud credentials

**Note**: The agent uses a single generic secret (`model-api-key`) that can hold either OpenAI or Gemini API key. See [Generic API Key Secret Guide](docs/generic-api-key-secret.md) for details.

See [Setup Guide](docs/sreagent-setup.md) and [OpenAI Configuration](docs/openai-configuration.md) for detailed configuration options.

## License

Apache 2.0

## Contributing

See CONTRIBUTING.md for guidelines.

