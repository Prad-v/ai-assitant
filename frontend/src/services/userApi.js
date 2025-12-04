import axios from 'axios';

// Get API base URL from environment or use default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000' : '/api');

// Create axios instance for user API
const userApiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Add token to requests
userApiClient.interceptors.request.use(
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
userApiClient.interceptors.response.use(
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

export const listUsers = async () => {
  try {
    const response = await userApiClient.get('/users');
    return response.data;
  } catch (error) {
    console.error('Error listing users:', error);
    throw error.response?.data || { detail: error.message || 'Failed to list users' };
  }
};

export const createUser = async (userData) => {
  try {
    const response = await userApiClient.post('/users', userData);
    return response.data;
  } catch (error) {
    console.error('Error creating user:', error);
    throw error.response?.data || { detail: error.message || 'Failed to create user' };
  }
};

export const updateUser = async (userId, userData) => {
  try {
    const response = await userApiClient.put(`/users/${userId}`, userData);
    return response.data;
  } catch (error) {
    console.error('Error updating user:', error);
    throw error.response?.data || { detail: error.message || 'Failed to update user' };
  }
};

export const deleteUser = async (userId) => {
  try {
    const response = await userApiClient.delete(`/users/${userId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting user:', error);
    throw error.response?.data || { detail: error.message || 'Failed to delete user' };
  }
};

export const resetPassword = async (userId, newPassword) => {
  try {
    const response = await userApiClient.post(`/users/${userId}/reset-password`, {
      new_password: newPassword,
    });
    return response.data;
  } catch (error) {
    console.error('Error resetting password:', error);
    throw error.response?.data || { detail: error.message || 'Failed to reset password' };
  }
};

