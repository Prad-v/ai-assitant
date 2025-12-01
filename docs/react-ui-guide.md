# React UI Guide

## Overview

The SRE Agent includes a modern React-based frontend UI that provides an intuitive chat interface for interacting with the Kubernetes troubleshooting and security review agent. The React UI runs as a separate service alongside the ADK web interface.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   React UI      │────────►│  FastAPI Server  │────────►│  ADK Agent      │
│  (Port 3000)    │  HTTP   │   (Port 8000)     │         │  + MCP Tools    │
│  (Separate Pod) │         │  (Existing)       │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

## Features

- **Modern Chat Interface**: Clean, responsive chat UI
- **Session Management**: Maintains conversation context
- **Real-time Communication**: Direct integration with FastAPI backend
- **Error Handling**: User-friendly error messages
- **Loading States**: Visual feedback during API calls
- **Responsive Design**: Works on desktop and mobile devices

## Accessing the React UI

### Local Development

#### Using Docker Compose

```bash
# Start all services
docker compose up -d

# Access React UI
# Open browser to http://localhost:3000
```

#### Using npm (Development Mode)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Access at http://localhost:3000
```

### Kubernetes Deployment

#### Port Forward

```bash
# Port forward to React UI service
kubectl port-forward -n sreagent svc/sreagent-frontend 3000:3000

# Access at http://localhost:3000
```

#### Via Ingress

If ingress is enabled:

```bash
# Add to /etc/hosts (or configure DNS)
echo "127.0.0.1 sreagent-ui.local" | sudo tee -a /etc/hosts

# Access at http://sreagent-ui.local
```

## Using the React UI

### Basic Usage

1. **Open the UI**: Navigate to the React UI URL (http://localhost:3000 or your configured host)

2. **Start Chatting**: Type your questions in the message input at the bottom

3. **Send Messages**: 
   - Press Enter to send
   - Shift+Enter for new line

4. **View Responses**: Agent responses appear in the chat interface

### Example Queries

**SRE Troubleshooting:**
- "List all pods in the default namespace"
- "Why is my pod in CrashLoopBackOff?"
- "Show me the logs for pod my-app-123"
- "Check the health of all deployments"
- "Get me the list of deployments missing liveness/readiness probes"

**Security Review:**
- "Review security of all deployments in default namespace"
- "Perform security analysis of the test-app deployment"
- "Check if any pods are running as root"
- "Recommend Kyverno policies for enforcing non-root containers"

## API Integration

The React UI communicates with the FastAPI backend via REST API:

### Endpoints Used

- **POST /chat**: Send messages to the agent
  ```json
  {
    "message": "Your question here",
    "user_id": "web_user",
    "session_id": "session_123" // Optional, auto-generated
  }
  ```

- **GET /health**: Check backend health status

### Configuration

The API base URL is configured via environment variable:

- **Development**: `VITE_API_BASE_URL=http://localhost:8000/api`
- **Production**: Automatically uses service discovery (`http://sreagent:8000/api`)

## Development

### Prerequisites

- Node.js 20+ and npm
- Docker (for containerized development)

### Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Build for Production

```bash
# Build the React app
npm run build

# Preview production build
npm run preview
```

### Project Structure

```
frontend/
├── public/
│   └── index.html          # HTML template
├── src/
│   ├── components/
│   │   ├── Chat.jsx        # Main chat component
│   │   ├── MessageList.jsx # Message display component
│   │   └── MessageInput.jsx # Input component
│   ├── services/
│   │   └── api.js          # API client
│   ├── styles/
│   │   ├── index.css       # Global styles
│   │   ├── App.css         # App component styles
│   │   ├── Chat.css        # Chat component styles
│   │   └── MessageInput.css # Input component styles
│   ├── App.jsx             # Main App component
│   └── index.jsx           # Entry point
├── Dockerfile              # Multi-stage Docker build
├── nginx.conf              # Nginx configuration
├── package.json            # Dependencies
└── vite.config.js          # Vite configuration
```

## Docker Build

### Build Frontend Image

```bash
# Build from frontend directory
cd frontend
docker build -t sreagent-frontend:0.1.0 .

# Or use Makefile
make frontend-docker-build
```

### Multi-stage Build

The Dockerfile uses a multi-stage build:
1. **Builder stage**: Node.js to build React app
2. **Production stage**: Nginx to serve static files

## Kubernetes Deployment

### Helm Configuration

The frontend is deployed via Helm chart:

```yaml
frontend:
  enabled: true
  replicaCount: 1
  image:
    repository: sreagent-frontend
    tag: "0.1.0"
  port: 3000
  service:
    type: ClusterIP
    port: 3000
  ingress:
    enabled: false
```

### Deploy with Helm

```bash
# Build and push images
make frontend-docker-build frontend-docker-push

# Deploy via Helm
helm upgrade --install sreagent ./helm/sreagent \
  --namespace sreagent \
  --set frontend.image.repository=your-registry/sreagent-frontend \
  --set frontend.image.tag=0.1.0
```

## Troubleshooting

### UI Not Loading

1. **Check Pod Status**:
   ```bash
   kubectl get pods -n sreagent -l app.kubernetes.io/component=frontend
   ```

2. **Check Logs**:
   ```bash
   kubectl logs -n sreagent -l app.kubernetes.io/component=frontend
   ```

3. **Verify Service**:
   ```bash
   kubectl get svc -n sreagent sreagent-frontend
   ```

### API Connection Issues

1. **Check Backend Health**:
   ```bash
   kubectl exec -n sreagent deployment/sreagent-frontend -- \
     curl http://sreagent:8000/health
   ```

2. **Verify CORS Configuration**:
   - Check `backend/services/sreagent/server.py` for CORS settings
   - Ensure `allow_origins` includes the frontend URL

3. **Check Network Policies**:
   - Verify frontend can reach backend service
   - Check service names and ports

### Build Issues

1. **Node Version**: Ensure Node.js 20+ is used
2. **Dependencies**: Run `npm install` to update dependencies
3. **Build Errors**: Check `npm run build` output for errors

## Configuration

### Environment Variables

- `VITE_API_BASE_URL`: API backend URL (default: auto-detected)
- `PORT`: Nginx port (default: 3000)

### Nginx Configuration

The nginx configuration (`nginx.conf`) handles:
- Serving static React files
- Proxying API calls to backend
- Gzip compression
- Security headers
- Static asset caching

## Comparison with ADK Web Interface

| Feature | React UI | ADK Web UI |
|---------|----------|------------|
| **Location** | Port 3000 | Port 8000 /dev-ui/ |
| **Interface** | Custom React | ADK Built-in |
| **Styling** | Custom CSS | ADK Default |
| **Features** | Basic Chat | Full ADK Features |
| **Deployment** | Separate Service | Same Pod as Backend |

Both interfaces are available:
- **React UI**: Modern, customizable interface
- **ADK Web UI**: Full-featured ADK interface with advanced capabilities

## Future Enhancements

- Streaming responses (WebSocket/SSE)
- Message history persistence
- Role switching UI (SRE/Security Reviewer)
- Tool execution visibility
- Session management UI
- Dark/light theme toggle
- Export chat history
- Code syntax highlighting
- Markdown rendering improvements

## References

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)

