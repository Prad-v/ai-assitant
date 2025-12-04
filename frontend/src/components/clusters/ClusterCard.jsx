import React from 'react';
import '../../styles/ClusterCard.css';

const ClusterCard = ({ cluster, onView, onTest, onDelete, onEdit, isTesting }) => {
  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateString;
    }
  };

  const getStatusClass = (status) => {
    const statusLower = (status || 'unknown').toLowerCase();
    if (statusLower === 'connected') return 'connected';
    if (statusLower === 'disconnected') return 'disconnected';
    if (statusLower === 'error') return 'error';
    return 'unknown';
  };

  const statusClass = getStatusClass(cluster.status);

  return (
    <div className={`cluster-card ${isTesting ? 'loading' : ''}`} onClick={() => onView && onView(cluster)}>
      <div className="cluster-card-header">
        <h3 className="cluster-name">{cluster.name}</h3>
        <span className={`cluster-status ${statusClass}`}>
          <span className="status-dot"></span>
          {cluster.status || 'unknown'}
        </span>
      </div>
      
      {cluster.description && (
        <p className="cluster-description">{cluster.description}</p>
      )}
      
      {cluster.tags && cluster.tags.length > 0 && (
        <div className="cluster-tags">
          {cluster.tags.map((tag, index) => (
            <span key={index} className="cluster-tag">{tag}</span>
          ))}
        </div>
      )}
      
      <div className="cluster-meta">
        <span>Last checked: {formatDate(cluster.last_checked)}</span>
        <div className="cluster-actions" onClick={(e) => e.stopPropagation()}>
          {onTest && (
            <button
              className="action-button"
              onClick={() => onTest(cluster.id)}
              disabled={isTesting}
              title="Test connection"
            >
              Test
            </button>
          )}
          {onEdit && (
            <button
              className="action-button"
              onClick={() => onEdit(cluster)}
              title="Edit cluster"
            >
              Edit
            </button>
          )}
          {onDelete && (
            <button
              className="action-button danger"
              onClick={() => {
                if (window.confirm(`Are you sure you want to delete cluster "${cluster.name}"?`)) {
                  onDelete(cluster.id);
                }
              }}
              title="Delete cluster"
            >
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ClusterCard;

