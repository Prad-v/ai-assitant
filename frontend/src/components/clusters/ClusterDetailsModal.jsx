import React, { useState, useEffect } from 'react';
import '../../styles/Modal.css';
import { getClusterInfo, testClusterConnection } from '../../services/clusterApi';

const ClusterDetailsModal = ({ isOpen, onClose, cluster, onTest }) => {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (isOpen && cluster) {
      loadDetails();
    }
  }, [isOpen, cluster]);

  const loadDetails = async () => {
    if (!cluster) return;
    
    setLoading(true);
    try {
      const info = await getClusterInfo(cluster.id);
      setDetails(info);
    } catch (error) {
      console.error('Failed to load cluster details:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    if (!cluster) return;
    
    setTesting(true);
    try {
      const result = await testClusterConnection(cluster.id);
      if (onTest) {
        onTest(cluster.id, result);
      }
      // Reload details after test
      await loadDetails();
    } catch (error) {
      console.error('Connection test failed:', error);
    } finally {
      setTesting(false);
    }
  };

  if (!isOpen || !cluster) return null;

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return dateString;
    }
  };

  const connectionInfo = details?.connection || {};

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Cluster Details: {cluster.name}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          {loading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Loading cluster details...</p>
            </div>
          ) : (
            <>
              <div className="details-section">
                <h3>Basic Information</h3>
                <div className="details-grid">
                  <div className="detail-item">
                    <label>Cluster ID:</label>
                    <span>{cluster.id}</span>
                  </div>
                  <div className="detail-item">
                    <label>Name:</label>
                    <span>{cluster.name}</span>
                  </div>
                  <div className="detail-item">
                    <label>Description:</label>
                    <span>{cluster.description || 'No description'}</span>
                  </div>
                  <div className="detail-item">
                    <label>Status:</label>
                    <span className={`status-badge status-${cluster.status || 'unknown'}`}>
                      {cluster.status || 'unknown'}
                    </span>
                  </div>
                  <div className="detail-item">
                    <label>Created:</label>
                    <span>{formatDate(cluster.created_at)}</span>
                  </div>
                  <div className="detail-item">
                    <label>Last Updated:</label>
                    <span>{formatDate(cluster.updated_at)}</span>
                  </div>
                  <div className="detail-item">
                    <label>Last Checked:</label>
                    <span>{formatDate(cluster.last_checked)}</span>
                  </div>
                  {cluster.tags && cluster.tags.length > 0 && (
                    <div className="detail-item full-width">
                      <label>Tags:</label>
                      <div className="tags-list">
                        {cluster.tags.map((tag, index) => (
                          <span key={index} className="tag">{tag}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="details-section">
                <div className="section-header">
                  <h3>Connection Status</h3>
                  <button
                    onClick={handleTest}
                    disabled={testing}
                    className="button-primary button-small"
                  >
                    {testing ? 'Testing...' : 'Test Connection'}
                  </button>
                </div>
                {connectionInfo.connected ? (
                  <div className="connection-success">
                    <p>✓ Successfully connected to cluster</p>
                    {connectionInfo.namespace_count !== undefined && (
                      <p>Found {connectionInfo.namespace_count} namespaces</p>
                    )}
                    {connectionInfo.message && (
                      <p>{connectionInfo.message}</p>
                    )}
                  </div>
                ) : connectionInfo.error ? (
                  <div className="connection-error">
                    <p>✗ Connection failed</p>
                    <p className="error-detail">{connectionInfo.error}</p>
                    {connectionInfo.http_status && (
                      <p className="error-detail">HTTP Status: {connectionInfo.http_status}</p>
                    )}
                  </div>
                ) : (
                  <p>Connection status unknown. Click "Test Connection" to verify.</p>
                )}
              </div>
            </>
          )}
        </div>
        
        <div className="modal-footer">
          <button onClick={onClose} className="button-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ClusterDetailsModal;

