import axios from 'axios';

// Cluster Inventory Service URL
// In production, this will be proxied through nginx to cluster-inventory service
// The nginx proxy routes /api/clusters/* to cluster-inventory service
const API_BASE_URL = import.meta.env.VITE_CLUSTER_INVENTORY_URL || 
  (import.meta.env.DEV ? 'http://localhost:8001' : '/api/clusters');

// Create axios instance for cluster API
const clusterApiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

// Add authentication tokens to requests
clusterApiClient.interceptors.request.use(
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
clusterApiClient.interceptors.response.use(
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
 * Cluster data model
 * @typedef {Object} Cluster
 * @property {string} id - Cluster ID
 * @property {string} name - Cluster name
 * @property {string} description - Cluster description
 * @property {string[]} tags - Cluster tags
 * @property {string} status - Connection status (connected, disconnected, error, unknown)
 * @property {string} created_at - Creation timestamp
 * @property {string} updated_at - Last update timestamp
 * @property {string|null} last_checked - Last connection check timestamp
 * @property {boolean} has_kubeconfig - Whether kubeconfig is stored
 */

/**
 * Register a new cluster
 * @param {Object} clusterData - Cluster data
 * @param {string} clusterData.name - Cluster name
 * @param {string} clusterData.kubeconfig - Kubeconfig file content
 * @param {string} [clusterData.description] - Optional description
 * @param {string[]} [clusterData.tags] - Optional tags
 * @returns {Promise<Cluster>}
 */
export const createCluster = async (clusterData) => {
  try {
    const response = await clusterApiClient.post('/clusters', clusterData);
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Failed to create cluster');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message || 'Failed to create cluster');
    }
  }
};

/**
 * List all clusters
 * @returns {Promise<Cluster[]>}
 */
export const listClusters = async () => {
  try {
    const response = await clusterApiClient.get('/clusters');
    // Ensure response.data is always an array
    const data = response.data;
    return Array.isArray(data) ? data : [];
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Failed to list clusters');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message || 'Failed to list clusters');
    }
  }
};

/**
 * Get cluster details
 * @param {string} clusterId - Cluster ID
 * @returns {Promise<Cluster>}
 */
export const getCluster = async (clusterId) => {
  try {
    const response = await clusterApiClient.get(`/clusters/${clusterId}`);
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Failed to get cluster');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message || 'Failed to get cluster');
    }
  }
};

/**
 * Update cluster
 * @param {string} clusterId - Cluster ID
 * @param {Object} updates - Cluster updates
 * @param {string} [updates.name] - New name
 * @param {string} [updates.description] - New description
 * @param {string[]} [updates.tags] - New tags
 * @param {string} [updates.kubeconfig] - New kubeconfig
 * @returns {Promise<Cluster>}
 */
export const updateCluster = async (clusterId, updates) => {
  try {
    const response = await clusterApiClient.put(`/clusters/${clusterId}`, updates);
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Failed to update cluster');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message || 'Failed to update cluster');
    }
  }
};

/**
 * Delete cluster
 * @param {string} clusterId - Cluster ID
 * @returns {Promise<Object>}
 */
export const deleteCluster = async (clusterId) => {
  try {
    const response = await clusterApiClient.delete(`/clusters/${clusterId}`);
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Failed to delete cluster');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message || 'Failed to delete cluster');
    }
  }
};

/**
 * Test cluster connection
 * @param {string} clusterId - Cluster ID
 * @returns {Promise<Object>}
 */
export const testClusterConnection = async (clusterId) => {
  try {
    const response = await clusterApiClient.post(`/clusters/${clusterId}/test`);
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Failed to test cluster connection');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message || 'Failed to test cluster connection');
    }
  }
};

/**
 * Get detailed cluster information
 * @param {string} clusterId - Cluster ID
 * @returns {Promise<Object>}
 */
export const getClusterInfo = async (clusterId) => {
  try {
    const response = await clusterApiClient.get(`/clusters/${clusterId}/info`);
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Failed to get cluster info');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error(error.message || 'Failed to get cluster info');
    }
  }
};

export default clusterApiClient;

