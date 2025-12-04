import React from 'react';
import ClusterCard from './ClusterCard';
import '../../styles/ClusterListView.css';

const ClusterListView = ({ clusters, viewMode, onView, onTest, onDelete, onEdit, testingClusterId }) => {
  if (!clusters || clusters.length === 0) {
    return null;
  }

  if (viewMode === 'list') {
    return (
      <div className="cluster-list-view">
        <table className="cluster-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Description</th>
              <th>Tags</th>
              <th>Last Checked</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {clusters.map((cluster) => (
              <tr key={cluster.id} className={testingClusterId === cluster.id ? 'testing' : ''}>
                <td>
                  <div className="cluster-name-cell">
                    <strong>{cluster.name}</strong>
                    {cluster.tags && cluster.tags.includes('auto-discovered') && (
                      <span className="auto-discovered-badge">Auto</span>
                    )}
                  </div>
                </td>
                <td>
                  <span className={`status-badge status-${cluster.status || 'unknown'}`}>
                    <span className="status-dot"></span>
                    {cluster.status || 'unknown'}
                  </span>
                </td>
                <td>
                  <div className="cluster-description-cell">
                    {cluster.description || '-'}
                  </div>
                </td>
                <td>
                  <div className="cluster-tags-cell">
                    {cluster.tags && cluster.tags.length > 0 ? (
                      cluster.tags.map((tag, index) => (
                        <span key={index} className="tag">{tag}</span>
                      ))
                    ) : (
                      '-'
                    )}
                  </div>
                </td>
                <td>
                  {cluster.last_checked ? new Date(cluster.last_checked).toLocaleString() : 'Never'}
                </td>
                <td>
                  <div className="cluster-actions-cell">
                    <button
                      className="action-button"
                      onClick={() => onTest && onTest(cluster.id)}
                      disabled={testingClusterId === cluster.id}
                      title="Test connection"
                    >
                      Test
                    </button>
                    <button
                      className="action-button"
                      onClick={() => onView && onView(cluster)}
                      title="View details"
                    >
                      View
                    </button>
                    <button
                      className="action-button"
                      onClick={() => onEdit && onEdit(cluster)}
                      title="Edit cluster"
                    >
                      Edit
                    </button>
                    <button
                      className="action-button danger"
                      onClick={() => {
                        if (window.confirm(`Are you sure you want to delete cluster "${cluster.name}"?`)) {
                          onDelete && onDelete(cluster.id);
                        }
                      }}
                      title="Delete cluster"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Tile view (existing grid view)
  return (
    <div className="clusters-grid">
      {clusters.map((cluster) => (
        <ClusterCard
          key={cluster.id}
          cluster={cluster}
          onView={onView}
          onTest={onTest}
          onDelete={onDelete}
          onEdit={onEdit}
          isTesting={testingClusterId === cluster.id}
        />
      ))}
    </div>
  );
};

export default ClusterListView;

