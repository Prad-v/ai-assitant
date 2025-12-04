"""Storage abstraction for cluster kubeconfig and metadata."""

import os
import base64
import logging
from typing import Optional, Dict, List
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

# Kubernetes client initialization
try:
    # Try to load in-cluster config first
    config.load_incluster_config()
    k8s_client = client.CoreV1Api()
except config.ConfigException:
    try:
        # Fallback to kubeconfig file
        config.load_kube_config()
        k8s_client = client.CoreV1Api()
    except Exception as e:
        logger.warning(f"Could not load Kubernetes config: {e}")
        k8s_client = None

NAMESPACE = os.getenv("NAMESPACE", "sreagent")
SECRET_PREFIX = "cluster-kubeconfig-"
CONFIGMAP_NAME = "cluster-inventory"


class ClusterStorage:
    """Manages storage of cluster kubeconfigs and metadata."""
    
    def __init__(self, namespace: str = NAMESPACE):
        self.namespace = namespace
        self.secret_prefix = SECRET_PREFIX
        self.configmap_name = CONFIGMAP_NAME
        
    def _get_secret_name(self, cluster_id: str) -> str:
        """Generate secret name for cluster kubeconfig."""
        return f"{self.secret_prefix}{cluster_id}"
    
    def store_kubeconfig(self, cluster_id: str, kubeconfig: str) -> bool:
        """
        Store kubeconfig as Kubernetes Secret.
        
        Args:
            cluster_id: Unique cluster identifier
            kubeconfig: Kubeconfig file content (YAML string)
            
        Returns:
            True if successful, False otherwise
        """
        if not k8s_client:
            logger.error("Kubernetes client not available")
            return False
            
        secret_name = self._get_secret_name(cluster_id)
        
        try:
            # Encode kubeconfig to base64
            kubeconfig_b64 = base64.b64encode(kubeconfig.encode('utf-8')).decode('utf-8')
            
            # Create or update secret
            secret = client.V1Secret(
                metadata=client.V1ObjectMeta(
                    name=secret_name,
                    namespace=self.namespace,
                    labels={
                        "app.kubernetes.io/name": "sreagent",
                        "app.kubernetes.io/component": "cluster-storage",
                        "cluster-id": cluster_id,
                    }
                ),
                type="Opaque",
                data={"kubeconfig": kubeconfig_b64}
            )
            
            try:
                # Try to get existing secret
                k8s_client.read_namespaced_secret(secret_name, self.namespace)
                # Update if exists
                k8s_client.replace_namespaced_secret(secret_name, self.namespace, secret)
                logger.info(f"Updated kubeconfig secret for cluster: {cluster_id}")
            except ApiException as e:
                if e.status == 404:
                    # Create if doesn't exist
                    k8s_client.create_namespaced_secret(self.namespace, secret)
                    logger.info(f"Created kubeconfig secret for cluster: {cluster_id}")
                else:
                    raise
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to store kubeconfig for cluster {cluster_id}: {e}")
            return False
    
    def get_kubeconfig(self, cluster_id: str) -> Optional[str]:
        """
        Retrieve kubeconfig from Kubernetes Secret.
        
        Args:
            cluster_id: Unique cluster identifier
            
        Returns:
            Kubeconfig content as string, or None if not found
        """
        if not k8s_client:
            logger.error("Kubernetes client not available")
            return None
            
        secret_name = self._get_secret_name(cluster_id)
        
        try:
            secret = k8s_client.read_namespaced_secret(secret_name, self.namespace)
            kubeconfig_b64 = secret.data.get("kubeconfig")
            if kubeconfig_b64:
                return base64.b64decode(kubeconfig_b64).decode('utf-8')
            return None
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Kubeconfig secret not found for cluster: {cluster_id}")
                return None
            logger.error(f"Failed to retrieve kubeconfig for cluster {cluster_id}: {e}")
            return None
    
    def delete_kubeconfig(self, cluster_id: str) -> bool:
        """
        Delete kubeconfig Secret.
        
        Args:
            cluster_id: Unique cluster identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not k8s_client:
            logger.error("Kubernetes client not available")
            return False
            
        secret_name = self._get_secret_name(cluster_id)
        
        try:
            k8s_client.delete_namespaced_secret(secret_name, self.namespace)
            logger.info(f"Deleted kubeconfig secret for cluster: {cluster_id}")
            return True
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Kubeconfig secret not found for cluster: {cluster_id}")
                return True  # Already deleted
            logger.error(f"Failed to delete kubeconfig for cluster {cluster_id}: {e}")
            return False
    
    def get_all_cluster_ids(self) -> List[str]:
        """
        Get list of all cluster IDs from Secrets.
        
        Returns:
            List of cluster IDs
        """
        if not k8s_client:
            logger.error("Kubernetes client not available")
            return []
            
        try:
            secrets = k8s_client.list_namespaced_secret(
                self.namespace,
                label_selector=f"app.kubernetes.io/name=sreagent,app.kubernetes.io/component=cluster-storage"
            )
            cluster_ids = []
            for secret in secrets.items:
                if secret.metadata.name.startswith(self.secret_prefix):
                    cluster_id = secret.metadata.name[len(self.secret_prefix):]
                    cluster_ids.append(cluster_id)
            return cluster_ids
        except Exception as e:
            logger.error(f"Failed to list cluster secrets: {e}")
            return []
    
    def store_metadata(self, cluster_id: str, metadata: Dict) -> bool:
        """
        Store cluster metadata in ConfigMap.
        
        Args:
            cluster_id: Unique cluster identifier
            metadata: Dictionary of metadata (name, description, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        if not k8s_client:
            logger.error("Kubernetes client not available")
            return False
            
        try:
            import json
            
            # Get existing ConfigMap or create new
            try:
                configmap = k8s_client.read_namespaced_config_map(
                    self.configmap_name, self.namespace
                )
                data = configmap.data or {}
            except ApiException as e:
                if e.status == 404:
                    data = {}
                else:
                    raise
            
            # Update metadata for this cluster
            data[cluster_id] = json.dumps(metadata)
            
            # Create or update ConfigMap
            configmap = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(
                    name=self.configmap_name,
                    namespace=self.namespace,
                    labels={
                        "app.kubernetes.io/name": "sreagent",
                        "app.kubernetes.io/component": "cluster-storage",
                    }
                ),
                data=data
            )
            
            try:
                k8s_client.read_namespaced_config_map(self.configmap_name, self.namespace)
                k8s_client.replace_namespaced_config_map(
                    self.configmap_name, self.namespace, configmap
                )
            except ApiException as e:
                if e.status == 404:
                    k8s_client.create_namespaced_config_map(self.namespace, configmap)
                    
            logger.info(f"Stored metadata for cluster: {cluster_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store metadata for cluster {cluster_id}: {e}")
            return False
    
    def get_metadata(self, cluster_id: str) -> Optional[Dict]:
        """
        Retrieve cluster metadata from ConfigMap.
        
        Args:
            cluster_id: Unique cluster identifier
            
        Returns:
            Metadata dictionary, or None if not found
        """
        if not k8s_client:
            logger.error("Kubernetes client not available")
            return None
            
        try:
            configmap = k8s_client.read_namespaced_config_map(
                self.configmap_name, self.namespace
            )
            data = configmap.data or {}
            metadata_json = data.get(cluster_id)
            if metadata_json:
                import json
                return json.loads(metadata_json)
            return None
        except ApiException as e:
            if e.status == 404:
                return None
            logger.error(f"Failed to retrieve metadata for cluster {cluster_id}: {e}")
            return None
    
    def delete_metadata(self, cluster_id: str) -> bool:
        """
        Delete cluster metadata from ConfigMap.
        
        Args:
            cluster_id: Unique cluster identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not k8s_client:
            logger.error("Kubernetes client not available")
            return False
            
        try:
            configmap = k8s_client.read_namespaced_config_map(
                self.configmap_name, self.namespace
            )
            data = configmap.data or {}
            if cluster_id in data:
                del data[cluster_id]
                configmap.data = data
                k8s_client.replace_namespaced_config_map(
                    self.configmap_name, self.namespace, configmap
                )
                logger.info(f"Deleted metadata for cluster: {cluster_id}")
            return True
        except ApiException as e:
            if e.status == 404:
                return True  # Already deleted
            logger.error(f"Failed to delete metadata for cluster {cluster_id}: {e}")
            return False

