"""Cluster registry service for managing cluster inventory."""

import uuid
import logging
from typing import Optional, Dict, List
from datetime import datetime
# Import using importlib since directory has hyphen
import importlib.util
import os

_base_dir = os.path.dirname(__file__)
_storage = importlib.util.spec_from_file_location("storage", os.path.join(_base_dir, "storage.py"))
_storage_module = importlib.util.module_from_spec(_storage)
_storage.loader.exec_module(_storage_module)

ClusterStorage = _storage_module.ClusterStorage

logger = logging.getLogger(__name__)


class ClusterRegistry:
    """Manages cluster inventory and metadata."""
    
    def __init__(self):
        self.storage = ClusterStorage()
    
    def register_cluster(
        self,
        name: str,
        kubeconfig: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Register a new cluster.
        
        Args:
            name: Cluster display name
            kubeconfig: Kubeconfig file content
            description: Optional cluster description
            tags: Optional list of tags
            
        Returns:
            Cluster ID if successful, None otherwise
        """
        # Generate unique cluster ID
        cluster_id = str(uuid.uuid4())
        
        # Store kubeconfig
        if not self.storage.store_kubeconfig(cluster_id, kubeconfig):
            logger.error(f"Failed to store kubeconfig for cluster: {name}")
            return None
        
        # Store metadata
        metadata = {
            "id": cluster_id,
            "name": name,
            "description": description or "",
            "tags": tags or [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "status": "unknown",  # Will be updated by connection test
            "last_checked": None,
        }
        
        if not self.storage.store_metadata(cluster_id, metadata):
            logger.error(f"Failed to store metadata for cluster: {name}")
            # Clean up kubeconfig if metadata storage fails
            self.storage.delete_kubeconfig(cluster_id)
            return None
        
        logger.info(f"Registered cluster: {name} (ID: {cluster_id})")
        return cluster_id
    
    def get_cluster(self, cluster_id: str) -> Optional[Dict]:
        """
        Get cluster information.
        
        Args:
            cluster_id: Cluster ID
            
        Returns:
            Cluster dictionary with metadata and kubeconfig availability, or None
        """
        metadata = self.storage.get_metadata(cluster_id)
        if not metadata:
            return None
        
        # Check if kubeconfig exists
        kubeconfig = self.storage.get_kubeconfig(cluster_id)
        metadata["has_kubeconfig"] = kubeconfig is not None
        
        return metadata
    
    def list_clusters(self) -> List[Dict]:
        """
        List all registered clusters.
        
        Returns:
            List of cluster dictionaries
        """
        cluster_ids = self.storage.get_all_cluster_ids()
        clusters = []
        
        for cluster_id in cluster_ids:
            cluster = self.get_cluster(cluster_id)
            if cluster:
                clusters.append(cluster)
        
        # Sort by name
        clusters.sort(key=lambda x: x.get("name", "").lower())
        return clusters
    
    def update_cluster(
        self,
        cluster_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        kubeconfig: Optional[str] = None
    ) -> bool:
        """
        Update cluster information.
        
        Args:
            cluster_id: Cluster ID
            name: New cluster name (optional)
            description: New description (optional)
            tags: New tags (optional)
            kubeconfig: New kubeconfig (optional)
            
        Returns:
            True if successful, False otherwise
        """
        metadata = self.storage.get_metadata(cluster_id)
        if not metadata:
            logger.error(f"Cluster not found: {cluster_id}")
            return False
        
        # Update metadata fields
        if name is not None:
            metadata["name"] = name
        if description is not None:
            metadata["description"] = description
        if tags is not None:
            metadata["tags"] = tags
        
        metadata["updated_at"] = datetime.utcnow().isoformat()
        
        # Update kubeconfig if provided
        if kubeconfig:
            if not self.storage.store_kubeconfig(cluster_id, kubeconfig):
                logger.error(f"Failed to update kubeconfig for cluster: {cluster_id}")
                return False
        
        # Store updated metadata
        if not self.storage.store_metadata(cluster_id, metadata):
            logger.error(f"Failed to update metadata for cluster: {cluster_id}")
            return False
        
        logger.info(f"Updated cluster: {cluster_id}")
        return True
    
    def delete_cluster(self, cluster_id: str) -> bool:
        """
        Delete a cluster.
        
        Args:
            cluster_id: Cluster ID
            
        Returns:
            True if successful, False otherwise
        """
        # Delete kubeconfig
        kubeconfig_deleted = self.storage.delete_kubeconfig(cluster_id)
        
        # Delete metadata
        metadata_deleted = self.storage.delete_metadata(cluster_id)
        
        if kubeconfig_deleted and metadata_deleted:
            logger.info(f"Deleted cluster: {cluster_id}")
            return True
        
        logger.warning(f"Partial deletion for cluster: {cluster_id}")
        return False
    
    def update_cluster_status(self, cluster_id: str, status: str, last_checked: Optional[str] = None) -> bool:
        """
        Update cluster connection status.
        
        Args:
            cluster_id: Cluster ID
            status: Status string (e.g., "connected", "disconnected", "error")
            last_checked: ISO timestamp of last check (optional)
            
        Returns:
            True if successful, False otherwise
        """
        metadata = self.storage.get_metadata(cluster_id)
        if not metadata:
            return False
        
        metadata["status"] = status
        if last_checked:
            metadata["last_checked"] = last_checked
        else:
            metadata["last_checked"] = datetime.utcnow().isoformat()
        metadata["updated_at"] = datetime.utcnow().isoformat()
        
        return self.storage.store_metadata(cluster_id, metadata)

