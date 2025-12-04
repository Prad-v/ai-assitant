import axios from 'axios';

// Get API base URL from environment or use default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.DEV ? 'http://localhost:8000' : '/api');

// Get admin token from localStorage or environment
const getAdminToken = () => {
  return localStorage.getItem('adminToken') || import.meta.env.VITE_ADMIN_TOKEN || '';
};

// Create axios instance for settings API
const settingsApiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

// Add authentication tokens to requests
settingsApiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    const sessionToken = localStorage.getItem('sessionToken');
    if (sessionToken) {
      config.headers['X-Session-Token'] = sessionToken;
    }
    // Fallback to admin token for backward compatibility
    const adminToken = getAdminToken();
    if (adminToken && !token) {
      config.headers['X-Admin-Token'] = adminToken;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle 401 responses
settingsApiClient.interceptors.response.use(
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
 * Get current model settings
 * @returns {Promise<{provider: string, model_name: string, max_tokens?: number, temperature?: number}>}
 */
export const getModelSettings = async () => {
  try {
    const response = await settingsApiClient.get('/settings/model');
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Failed to get model settings');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message || 'Failed to get model settings');
    }
  }
};

/**
 * Update model settings
 * @param {Object} settings - Model settings
 * @param {string} settings.provider - Model provider (e.g., "openai", "gemini")
 * @param {string} settings.model_name - Model name (e.g., "gpt-4", "gemini-2.0-flash")
 * @param {string} settings.api_key - API key
 * @param {number} [settings.max_tokens] - Optional max tokens
 * @param {number} [settings.temperature] - Optional temperature (0.0-2.0)
 * @returns {Promise<Object>}
 */
export const updateModelSettings = async (settings) => {
  try {
    // Clean the API key before sending (trim whitespace)
    const cleanedSettings = {
      ...settings,
      api_key: settings.api_key ? settings.api_key.trim() : settings.api_key,
      provider: settings.provider ? settings.provider.trim() : settings.provider,
      model_name: settings.model_name ? settings.model_name.trim() : settings.model_name,
    };
    
    const response = await settingsApiClient.put('/settings/model', cleanedSettings);
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Failed to update model settings');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message || 'Failed to update model settings');
    }
  }
};

/**
 * Validate API key without saving
 * @param {string} provider - Model provider
 * @param {string} modelName - Model name
 * @param {string} apiKey - API key to validate
 * @returns {Promise<{valid: boolean, message: string}>}
 */
export const validateApiKey = async (provider, modelName, apiKey) => {
  try {
    // Clean the API key before sending (trim whitespace)
    const cleanedApiKey = apiKey ? apiKey.trim() : '';
    
    if (!cleanedApiKey) {
      throw new Error('API key is required');
    }
    
    const response = await settingsApiClient.post('/settings/model/validate', {
      provider: provider ? provider.trim() : provider,
      model_name: modelName ? modelName.trim() : modelName,
      api_key: cleanedApiKey,
    });
    
    // Check if response has valid structure
    if (response.data && typeof response.data === 'object') {
      return response.data;
    }
    
    // Fallback if response structure is unexpected
    return { valid: false, message: 'Unexpected response format from server' };
  } catch (error) {
    // Log error for debugging
    console.error('API key validation error:', error);
    
    if (error.response) {
      // Backend returned an error response
      const errorMessage = error.response.data?.detail || 
                          error.response.data?.message || 
                          `Server error: ${error.response.status} ${error.response.statusText}`;
      throw new Error(errorMessage);
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      // This is likely a validation error we threw ourselves
      throw error;
    }
  }
};

/**
 * List available models for a provider
 * @param {string} provider - Model provider
 * @param {string} apiKey - API key
 * @returns {Promise<{success: boolean, models: string[], message: string}>}
 */
export const listAvailableModels = async (provider, apiKey) => {
  try {
    // Clean the API key before sending (trim whitespace)
    const cleanedApiKey = apiKey ? apiKey.trim() : '';
    
    const response = await settingsApiClient.post('/settings/models/list', {
      provider: provider ? provider.trim() : provider,
      api_key: cleanedApiKey,
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Failed to list models');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message || 'Failed to list models');
    }
  }
};

/**
 * Test saved model configuration using stored API key
 * @returns {Promise<{valid: boolean, message: string}>}
 */
export const testSavedConfiguration = async () => {
  try {
    const response = await settingsApiClient.post('/settings/model/test');
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Failed to test saved configuration');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message || 'Failed to test saved configuration');
    }
  }
};

/**
 * Reload agent with new settings
 * @returns {Promise<Object>}
 */
export const reloadAgent = async () => {
  try {
    const response = await settingsApiClient.post('/settings/model/reload');
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Failed to reload agent');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message || 'Failed to reload agent');
    }
  }
};

export default settingsApiClient;

