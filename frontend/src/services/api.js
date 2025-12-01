import axios from 'axios';

// Get API base URL from environment or use default
// In production (Kubernetes), use relative path /api which will be proxied by nginx
// In development, use localhost:8000
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.DEV ? 'http://localhost:8000' : '/api');

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60 seconds timeout for long-running queries
});

/**
 * Send a chat message to the agent
 * @param {string} message - User message
 * @param {string} userId - User identifier
 * @param {string} sessionId - Session identifier (optional)
 * @returns {Promise<{response: string, session_id: string}>}
 */
export const sendMessage = async (message, userId = 'default_user', sessionId = null) => {
  try {
    const response = await apiClient.post('/chat', {
      message,
      user_id: userId,
      session_id: sessionId,
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      // Server responded with error status
      throw new Error(error.response.data.detail || 'Failed to send message');
    } else if (error.request) {
      // Request made but no response
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      // Error in request setup
      throw new Error(error.message || 'Failed to send message');
    }
  }
};

/**
 * Check health status of the backend
 * @returns {Promise<{status: string, agent_ready: boolean, mcp_connected: boolean}>}
 */
export const checkHealth = async () => {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    throw new Error('Health check failed');
  }
};

export default apiClient;

