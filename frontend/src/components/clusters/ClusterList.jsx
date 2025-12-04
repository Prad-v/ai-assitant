import React from 'react';
import ClusterCard from './ClusterCard';

const ClusterList = ({ clusters, onView, onTest, onDelete, onEdit, testingClusterId }) => {
  // Ensure clusters is an array
  const clustersArray = Array.isArray(clusters) ? clusters : [];
  
  if (clustersArray.length === 0) {
    return null;
  }

  return (
    <div className="clusters-grid">
      {clustersArray.map((cluster) => (
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

export default ClusterList;

