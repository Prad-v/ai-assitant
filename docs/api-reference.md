# SRE Agent API Reference

## Base URL

- Local: `http://localhost:8000`
- Kubernetes: `http://sreagent.<namespace>.svc.cluster.local`

## Endpoints

### Health Check

Check the health status of the agent.

**Endpoint:** `GET /health`

**Response:**

```json
{
  "status": "healthy",
  "agent_ready": true,
  "mcp_connected": true
}
```

**Status Codes:**
- `200 OK`: Agent is healthy
- `503 Service Unavailable`: Agent not initialized

**Example:**

```bash
curl http://localhost:8000/health
```

---

### Root

Get service information.

**Endpoint:** `GET /`

**Response:**

```json
{
  "service": "SRE Agent",
  "version": "0.1.0",
  "status": "running",
  "endpoints": {
    "health": "/health",
    "chat": "/chat",
    "docs": "/docs"
  }
}
```

**Example:**

```bash
curl http://localhost:8000/
```

---

### Chat

Send a message to the agent and get a response.

**Endpoint:** `POST /chat`

**Request Body:**

```json
{
  "message": "List all pods in default namespace",
  "user_id": "user123",
  "session_id": "session456"
}
```

**Parameters:**
- `message` (string, required): The user's message/question
- `user_id` (string, optional): User identifier (default: "default_user")
- `session_id` (string, optional): Session identifier for conversation context

**Response:**

```json
{
  "response": "Here are the pods in the default namespace:\n\n1. pod-name-1\n2. pod-name-2\n...",
  "session_id": "session456"
}
```

**Status Codes:**
- `200 OK`: Request processed successfully
- `400 Bad Request`: Invalid request body
- `500 Internal Server Error`: Agent processing error
- `503 Service Unavailable`: Agent not initialized

**Example:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I check pod logs?",
    "user_id": "user123",
    "session_id": "session456"
  }'
```

**Example with session persistence:**

```bash
# First message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "My application is in the production namespace",
    "user_id": "user123",
    "session_id": "session456"
  }'

# Follow-up message (uses same session)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Check the logs for my application",
    "user_id": "user123",
    "session_id": "session456"
  }'
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message description"
}
```

**Common Error Codes:**
- `400 Bad Request`: Invalid request format
- `404 Not Found`: Endpoint not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service not ready

---

## Web Interface

The agent also provides an interactive web interface via FastAPI's automatic documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## Rate Limiting

Currently, no rate limiting is implemented. For production deployments, consider adding rate limiting middleware.

---

## Authentication

Currently, no authentication is required. For production deployments, add authentication middleware (API keys, OAuth, etc.).

---

## WebSocket Support (Future)

WebSocket support for streaming responses may be added in future versions.

---

## Examples

### Basic Troubleshooting Query

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Why is my pod in CrashLoopBackOff?",
    "user_id": "sre_team"
  }'
```

### List Resources

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "List all deployments in the kube-system namespace",
    "user_id": "admin"
  }'
```

### Get Logs

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me the last 100 lines of logs for pod my-app-123",
    "user_id": "developer"
  }'
```

### Helm Operations

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "List all Helm releases in the production namespace",
    "user_id": "operator"
  }'
```

---

## SDK Examples

### Python

```python
import requests

def chat_with_agent(message, user_id="default_user", session_id=None):
    url = "http://localhost:8000/chat"
    payload = {
        "message": message,
        "user_id": user_id,
    }
    if session_id:
        payload["session_id"] = session_id
    
    response = requests.post(url, json=payload)
    return response.json()

# Example usage
result = chat_with_agent("List all pods")
print(result["response"])
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

async function chatWithAgent(message, userId = 'default_user', sessionId = null) {
  const url = 'http://localhost:8000/chat';
  const payload = {
    message: message,
    user_id: userId,
  };
  
  if (sessionId) {
    payload.session_id = sessionId;
  }
  
  const response = await axios.post(url, payload);
  return response.data;
}

// Example usage
chatWithAgent('List all pods')
  .then(result => console.log(result.response))
  .catch(error => console.error(error));
```

---

## Versioning

API versioning is not currently implemented. All endpoints use the base path without version prefix.

Future versions may introduce versioning via URL path (`/v1/chat`) or headers.

