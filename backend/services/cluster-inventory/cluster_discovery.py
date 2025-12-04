"""Auto-discovery of in-cluster Kubernetes configuration."""

import os
import logging
from typing import Optional, Dict
from kubernetes import config as k8s_config
from kubernetes.client import CoreV1Api, ApiClient
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

# In-cluster service account paths
SERVICE_ACCOUNT_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
SERVICE_ACCOUNT_CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
SERVICE_ACCOUNT_NAMESPACE_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"

# Environment variables for in-cluster API server
KUBERNETES_SERVICE_HOST = os.getenv("KUBERNETES_SERVICE_HOST")
KUBERNETES_SERVICE_PORT = os.getenv("KUBERNETES_SERVICE_PORT", "443")


def is_running_in_cluster() -> bool:
    """
    Check if the application is running inside a Kubernetes cluster.
    
    Returns:
        True if running in-cluster, False otherwise
    """
    # Check if service account token exists
    token_exists = os.path.exists(SERVICE_ACCOUNT_TOKEN_PATH)
    ca_exists = os.path.exists(SERVICE_ACCOUNT_CA_PATH)
    namespace_exists = os.path.exists(SERVICE_ACCOUNT_NAMESPACE_PATH)
    
    # Check for Kubernetes service environment variables
    has_service_host = KUBERNETES_SERVICE_HOST is not None
    
    return token_exists and ca_exists and namespace_exists and has_service_host


def get_cluster_info() -> Optional[Dict[str, str]]:
    """
    Get cluster information when running in-cluster.
    
    Returns:
        Dictionary with cluster info (namespace, api_server) or None if not in-cluster
    """
    if not is_running_in_cluster():
        return None
    
    try:
        # Read namespace
        with open(SERVICE_ACCOUNT_NAMESPACE_PATH, 'r') as f:
            namespace = f.read().strip()
        
        # Get API server URL
        api_server = f"https://{KUBERNETES_SERVICE_HOST}:{KUBERNETES_SERVICE_PORT}"
        
        return {
            "namespace": namespace,
            "api_server": api_server,
            "host": KUBERNETES_SERVICE_HOST,
            "port": KUBERNETES_SERVICE_PORT,
        }
    except Exception as e:
        logger.error(f"Failed to get cluster info: {e}")
        return None


def generate_in_cluster_kubeconfig() -> Optional[str]:
    """
    Generate a kubeconfig YAML string for the in-cluster configuration.
    
    Returns:
        Kubeconfig YAML string, or None if not running in-cluster or generation fails
    """
    if not is_running_in_cluster():
        logger.debug("Not running in-cluster, cannot generate kubeconfig")
        return None
    
    try:
        # Read service account token
        with open(SERVICE_ACCOUNT_TOKEN_PATH, 'r') as f:
            token = f.read().strip()
        
        # Read CA certificate
        with open(SERVICE_ACCOUNT_CA_PATH, 'r') as f:
            ca_cert = f.read().strip()
        
        # Read namespace
        with open(SERVICE_ACCOUNT_NAMESPACE_PATH, 'r') as f:
            namespace = f.read().strip()
        
        # Get API server URL
        api_server = f"https://{KUBERNETES_SERVICE_HOST}:{KUBERNETES_SERVICE_PORT}"
        
        # Generate cluster name (use hostname or default)
        cluster_name = KUBERNETES_SERVICE_HOST or "kubernetes"
        
        # Generate kubeconfig YAML
        kubeconfig = f"""apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: {_base64_encode(ca_cert)}
    server: {api_server}
  name: {cluster_name}
contexts:
- context:
    cluster: {cluster_name}
    namespace: {namespace}
    user: in-cluster-service-account
  name: in-cluster-context
current-context: in-cluster-context
users:
- name: in-cluster-service-account
  user:
    token: {token}
"""
        return kubeconfig
        
    except Exception as e:
        logger.error(f"Failed to generate in-cluster kubeconfig: {e}")
        return None


def _base64_encode(data: str) -> str:
    """Base64 encode a string."""
    import base64
    return base64.b64encode(data.encode('utf-8')).decode('utf-8')


def get_cluster_name() -> str:
    """
    Get a friendly name for the in-cluster configuration.
    
    Returns:
        Cluster name string
    """
    if not is_running_in_cluster():
        return "local-cluster"
    
    try:
        # Try to get cluster name from API server
        k8s_config.load_incluster_config()
        api_client = ApiClient()
        core_api = CoreV1Api(api_client)
        
        # Try to get cluster info from a well-known resource
        try:
            # Get current namespace
            with open(SERVICE_ACCOUNT_NAMESPACE_PATH, 'r') as f:
                namespace = f.read().strip()
            
            # Try to get cluster name from node labels or use hostname
            try:
                nodes = core_api.list_node(limit=1)
                if nodes.items:
                    node = nodes.items[0]
                    # Try to get cluster name from node labels
                    labels = node.metadata.labels or {}
                    cluster_name = (
                        labels.get("cluster-name") or
                        labels.get("kubernetes.io/cluster-name") or
                        labels.get("cluster") or
                        KUBERNETES_SERVICE_HOST or
                        "kubernetes"
                    )
                else:
                    cluster_name = KUBERNETES_SERVICE_HOST or "kubernetes"
            except Exception:
                cluster_name = KUBERNETES_SERVICE_HOST or "kubernetes"
            
            # Use namespace as part of the name if available
            if namespace and namespace != "default":
                return f"in-cluster-{cluster_name}-{namespace}"
            else:
                return f"in-cluster-{cluster_name}"
        except Exception:
            # Fallback to service host
            return f"in-cluster-{KUBERNETES_SERVICE_HOST or 'kubernetes'}"
    except Exception as e:
        logger.warning(f"Could not determine cluster name: {e}")
        return f"in-cluster-{KUBERNETES_SERVICE_HOST or 'kubernetes'}"


def discover_and_register_cluster(cluster_registry, force: bool = False) -> Optional[str]:
    """
    Discover in-cluster configuration and register it in the inventory.
    
    Args:
        cluster_registry: ClusterRegistry instance to use for registration
        force: If True, re-register even if already exists (default: False)
        
    Returns:
        Cluster ID if successfully registered, None otherwise
    """
    if not is_running_in_cluster():
        logger.info("Not running in-cluster, skipping auto-discovery")
        return None
    
    try:
        # Check if cluster is already registered (unless forcing)
        if not force:
            existing_clusters = cluster_registry.list_clusters()
            cluster_name = get_cluster_name()
            
            # Check if we already have a cluster with this name or similar
            for cluster in existing_clusters:
                if cluster.get("name") == cluster_name or "in-cluster" in cluster.get("name", "").lower():
                    logger.info(f"In-cluster cluster already registered: {cluster.get('id')}")
                    return cluster.get("id")
        else:
            cluster_name = get_cluster_name()
        
        # Generate kubeconfig
        kubeconfig = generate_in_cluster_kubeconfig()
        if not kubeconfig:
            logger.error("Failed to generate in-cluster kubeconfig")
            return None
        
        # Get cluster info for description
        cluster_info = get_cluster_info()
        description = f"Auto-discovered in-cluster configuration"
        if cluster_info:
            description += f" (namespace: {cluster_info.get('namespace', 'unknown')}, API: {cluster_info.get('api_server', 'unknown')})"
        
        # Register the cluster
        cluster_id = cluster_registry.register_cluster(
            name=cluster_name,
            kubeconfig=kubeconfig,
            description=description,
            tags=["auto-discovered", "in-cluster"]
        )
        
        if cluster_id:
            logger.info(f"Successfully auto-registered in-cluster configuration: {cluster_id}")
            return cluster_id
        else:
            logger.error("Failed to register in-cluster configuration")
            return None
            
    except Exception as e:
        logger.error(f"Error during cluster auto-discovery: {e}", exc_info=True)
        return None

