import axios from 'axios';

// Get API base URL from environment or use default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000' : '/api');

// Create axios instance for token API
const tokenApiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Add token to requests
tokenApiClient.interceptors.request.use(
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
tokenApiClient.interceptors.response.use(
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

export const listTokens = async () => {
  try {
    const response = await tokenApiClient.get('/tokens');
    return response.data;
  } catch (error) {
    console.error('Error listing tokens:', error);
    throw error.response?.data || { detail: error.message || 'Failed to list tokens' };
  }
};

export const createToken = async (tokenData) => {
  try {
    const response = await tokenApiClient.post('/tokens', tokenData);
    return response.data;
  } catch (error) {
    console.error('Error creating token:', error);
    throw error.response?.data || { detail: error.message || 'Failed to create token' };
  }
};

export const revokeToken = async (tokenId) => {
  try {
    const response = await tokenApiClient.delete(`/tokens/${tokenId}`);
    return response.data;
  } catch (error) {
    console.error('Error revoking token:', error);
    throw error.response?.data || { detail: error.message || 'Failed to revoke token' };
  }
};

