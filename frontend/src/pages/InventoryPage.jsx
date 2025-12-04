import React, { useState, useEffect } from 'react';
import ClusterListView from '../components/clusters/ClusterListView';
import UploadClusterModal from '../components/clusters/UploadClusterModal';
import ClusterDetailsModal from '../components/clusters/ClusterDetailsModal';
import { listClusters, createCluster, deleteCluster, testClusterConnection } from '../services/clusterApi';
import '../styles/InventoryPage.css';

const InventoryPage = () => {
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [testingClusterId, setTestingClusterId] = useState(null);
  const [viewMode, setViewMode] = useState('list'); // 'list' or 'tile'

  useEffect(() => {
    loadClusters();
  }, []);

  const loadClusters = async () => {
    setLoading(true);
    setError(null);
    try {
      const clusterList = await listClusters();
      // Ensure clusterList is an array
      const clustersArray = Array.isArray(clusterList) ? clusterList : [];
      setClusters(clustersArray);
    } catch (err) {
      setError(err.message || 'Failed to load clusters');
      console.error('Failed to load clusters:', err);
      // Set empty array on error to prevent .find() errors
      setClusters([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCluster = async (clusterData) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const newCluster = await createCluster(clusterData);
      setClusters([...clusters, newCluster]);
      setIsUploadModalOpen(false);
    } catch (err) {
      setError(err.message || 'Failed to create cluster');
      throw err; // Re-throw to let modal handle it
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteCluster = async (clusterId) => {
    try {
      await deleteCluster(clusterId);
      setClusters(Array.isArray(clusters) ? clusters.filter(c => c && c.id !== clusterId) : []);
    } catch (err) {
      setError(err.message || 'Failed to delete cluster');
      alert(`Failed to delete cluster: ${err.message}`);
    }
  };

  const handleTestCluster = async (clusterId) => {
    setTestingClusterId(clusterId);
    setError(null);
    try {
      const result = await testClusterConnection(clusterId);
      // Reload clusters to update status
      await loadClusters();
      
      if (result.connected) {
        // Show success message
        console.log(`Cluster ${clusterId} connection test successful`);
      } else {
        setError(`Connection test failed: ${result.error || 'Unknown error'}`);
      }
    } catch (err) {
      setError(err.message || 'Failed to test cluster connection');
    } finally {
      setTestingClusterId(null);
    }
  };

  const handleViewCluster = (cluster) => {
    setSelectedCluster(cluster);
    setIsDetailsModalOpen(true);
  };

  const handleEditCluster = (cluster) => {
    // TODO: Implement edit functionality
    alert('Edit functionality coming soon');
  };

  return (
    <div className="inventory-page">
      <div className="inventory-header">
        <div>
          <h1>Cluster Inventory</h1>
          <p className="subtitle">Manage Kubernetes cluster configurations</p>
        </div>
        <div className="header-actions">
          <div className="view-toggle">
            <button
              onClick={() => setViewMode('list')}
              className={`view-toggle-button ${viewMode === 'list' ? 'active' : ''}`}
              title="List view"
            >
              <span>☰</span> List
            </button>
            <button
              onClick={() => setViewMode('tile')}
              className={`view-toggle-button ${viewMode === 'tile' ? 'active' : ''}`}
              title="Tile view"
            >
              <span>⊞</span> Tile
            </button>
          </div>
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="button-primary"
          >
            + Add Cluster
          </button>
        </div>
      </div>

      <div className="inventory-content">
        {error && (
          <div className="error-banner">
            <span className="error-icon">⚠</span>
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer' }}
            >
              ×
            </button>
          </div>
        )}

        {loading ? (
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Loading clusters...</p>
          </div>
        ) : clusters.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📦</div>
            <h3>No clusters registered</h3>
            <p>Get started by adding your first Kubernetes cluster. Upload a kubeconfig file to begin.</p>
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="button-primary"
            >
              Add Your First Cluster
            </button>
          </div>
        ) : (
          <ClusterListView
            clusters={clusters}
            viewMode={viewMode}
            onView={handleViewCluster}
            onTest={handleTestCluster}
            onDelete={handleDeleteCluster}
            onEdit={handleEditCluster}
            testingClusterId={testingClusterId}
          />
        )}
      </div>

      <UploadClusterModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSubmit={handleCreateCluster}
        isSubmitting={isSubmitting}
      />

      <ClusterDetailsModal
        isOpen={isDetailsModalOpen}
        onClose={() => {
          setIsDetailsModalOpen(false);
          setSelectedCluster(null);
        }}
        cluster={selectedCluster}
        onTest={(clusterId, result) => {
          handleTestCluster(clusterId);
        }}
      />
    </div>
  );
};

export default InventoryPage;

