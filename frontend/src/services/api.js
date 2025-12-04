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

// Add authentication tokens to requests
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    const sessionToken = localStorage.getItem('sessionToken');
    if (sessionToken) {
      config.headers['X-Session-Token'] = sessionToken;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle 401 responses
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('sessionToken');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

/**
 * Send a chat message to the agent
 * @param {string} message - User message
 * @param {string} sessionId - Session identifier (optional)
 * @param {string} clusterId - Cluster ID for multi-cluster support (optional)
 * @returns {Promise<{response: string, session_id: string}>}
 */
export const sendMessage = async (message, sessionId = null, clusterId = null) => {
  try {
    const payload = {
      message,
      session_id: sessionId,
    };
    if (clusterId) {
      payload.cluster_id = clusterId;
    }
    const response = await apiClient.post('/chat', payload);
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

