"""Cluster management and connection testing."""

import os
import tempfile
import logging
from typing import Optional, Dict
from datetime import datetime
from kubernetes import config as k8s_config
from kubernetes.client import ApiClient, CoreV1Api
from kubernetes.client.rest import ApiException

# Import using importlib since directory has hyphen
import importlib.util
import os

_base_dir = os.path.dirname(__file__)
_cluster_registry = importlib.util.spec_from_file_location("cluster_registry", os.path.join(_base_dir, "cluster_registry.py"))
_cluster_registry_module = importlib.util.module_from_spec(_cluster_registry)
_cluster_registry.loader.exec_module(_cluster_registry_module)

_storage = importlib.util.spec_from_file_location("storage", os.path.join(_base_dir, "storage.py"))
_storage_module = importlib.util.module_from_spec(_storage)
_storage.loader.exec_module(_storage_module)

ClusterRegistry = _cluster_registry_module.ClusterRegistry
ClusterStorage = _storage_module.ClusterStorage

logger = logging.getLogger(__name__)


class ClusterManager:
    """Manages cluster operations including connection testing."""
    
    def __init__(self):
        self.registry = ClusterRegistry()
        self.storage = ClusterStorage()
    
    def test_connection(self, cluster_id: str) -> Dict[str, any]:
        """
        Test connection to a Kubernetes cluster.
        
        Args:
            cluster_id: Cluster ID to test
            
        Returns:
            Dictionary with connection status and details
        """
        kubeconfig = self.storage.get_kubeconfig(cluster_id)
        if not kubeconfig:
            return {
                "connected": False,
                "error": "Kubeconfig not found",
                "status": "error"
            }
        
        # Write kubeconfig to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
            f.write(kubeconfig)
            temp_kubeconfig = f.name
        
        try:
            # Load kubeconfig
            # For in-cluster configs, we need to handle them specially
            # Check if this is an in-cluster kubeconfig by checking if it uses the same API server
            import os
            is_in_cluster_config = False
            if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
                # Check if kubeconfig points to the same cluster we're running in
                k8s_service_host = os.getenv("KUBERNETES_SERVICE_HOST")
                if k8s_service_host and k8s_service_host in kubeconfig:
                    # This is likely the in-cluster config - use incluster config directly
                    is_in_cluster_config = True
                    k8s_config.load_incluster_config()
                else:
                    k8s_config.load_kube_config(config_file=temp_kubeconfig)
            else:
                k8s_config.load_kube_config(config_file=temp_kubeconfig)
            
            # Test connection by getting cluster info
            api_client = ApiClient()
            core_api = CoreV1Api(api_client)
            
            # Try to get cluster version (lightweight check, no permissions needed)
            try:
                # Get server version (lightweight check, no permissions needed)
                # This endpoint is public and doesn't require any RBAC permissions
                version_response = api_client.call_api(
                    '/version',
                    'GET',
                    auth_settings=['BearerToken'],
                    response_type='object',
                    _preload_content=False
                )
                
                # If we got here, the connection works. Try optional checks for more info
                namespace_count = None
                try:
                    # For in-cluster, try to access resources in our namespace
                    if is_in_cluster_config:
                        import os
                        current_ns = os.getenv("NAMESPACE") or os.getenv("POD_NAMESPACE", "sreagent")
                        try:
                            # Try listing pods in our namespace (we should have this permission)
                            pods = core_api.list_namespaced_pod(current_ns, limit=1)
                            namespace_count = 1  # We can access at least our namespace
                        except ApiException:
                            # If we can't list pods, that's okay - version check confirmed connection
                            pass
                    else:
                        # For external clusters, try to list namespaces (may fail due to RBAC)
                        try:
                            namespaces = core_api.list_namespace(limit=1)
                            namespace_count = len(namespaces.items) if namespaces.items else 0
                        except ApiException:
                            # If we can't list namespaces, that's okay - connection still works
                            # The version endpoint already confirmed we can connect
                            pass
                except Exception:
                    # If additional checks fail, that's okay - version check already confirmed connection
                    pass
                
                # Update cluster status
                self.registry.update_cluster_status(
                    cluster_id,
                    "connected",
                    datetime.utcnow().isoformat()
                )
                
                # Build success message
                if is_in_cluster_config:
                    message = "Successfully connected to in-cluster configuration."
                elif namespace_count is not None:
                    message = f"Successfully connected. Found {namespace_count} namespaces."
                else:
                    message = "Successfully connected to cluster."
                
                return {
                    "connected": True,
                    "status": "connected",
                    "namespace_count": namespace_count,
                    "message": message
                }
                
            except ApiException as e:
                # Check if it's a permission error vs actual connection failure
                if e.status == 401:
                    error_msg = f"Authentication failed: {e.reason}"
                elif e.status == 403:
                    # 403 means we connected but don't have permission - connection still works!
                    # This is common for in-cluster configs with limited RBAC
                    logger.info(f"Connection test for cluster {cluster_id}: Connected but limited permissions (403)")
                    self.registry.update_cluster_status(
                        cluster_id,
                        "connected",
                        datetime.utcnow().isoformat()
                    )
                    return {
                        "connected": True,
                        "status": "connected",
                        "message": "Successfully connected. Some operations may require additional permissions.",
                        "warning": f"Limited permissions: {e.reason}"
                    }
                else:
                    error_msg = f"API error: {e.reason}"
                
                if e.status not in [403]:  # Don't log 403 as error since connection works
                    logger.error(f"Connection test failed for cluster {cluster_id}: {error_msg}")
                
                if e.status not in [403]:
                    self.registry.update_cluster_status(
                        cluster_id,
                        "error",
                        datetime.utcnow().isoformat()
                    )
                    
                    return {
                        "connected": False,
                        "status": "error",
                        "error": error_msg,
                        "http_status": e.status
                    }
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Connection test failed for cluster {cluster_id}: {error_msg}")
            
            self.registry.update_cluster_status(
                cluster_id,
                "error",
                datetime.utcnow().isoformat()
            )
            
            return {
                "connected": False,
                "status": "error",
                "error": error_msg
            }
        
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_kubeconfig)
            except Exception:
                pass
    
    def get_cluster_info(self, cluster_id: str) -> Optional[Dict]:
        """
        Get detailed cluster information including connection status.
        
        Args:
            cluster_id: Cluster ID
            
        Returns:
            Dictionary with cluster information, or None if not found
        """
        cluster = self.registry.get_cluster(cluster_id)
        if not cluster:
            return None
        
        # Test connection and add status
        connection_test = self.test_connection(cluster_id)
        cluster["connection"] = connection_test
        
        return cluster
    
    def validate_kubeconfig(self, kubeconfig: str) -> Dict[str, any]:
        """
        Validate kubeconfig format and content.
        
        Args:
            kubeconfig: Kubeconfig file content
            
        Returns:
            Dictionary with validation result
        """
        if not kubeconfig or not kubeconfig.strip():
            return {
                "valid": False,
                "error": "Kubeconfig is empty"
            }
        
        # Basic YAML validation
        try:
            import yaml
            config_data = yaml.safe_load(kubeconfig)
            
            if not isinstance(config_data, dict):
                return {
                    "valid": False,
                    "error": "Invalid kubeconfig format: not a dictionary"
                }
            
            # Check for required fields
            if "apiVersion" not in config_data:
                return {
                    "valid": False,
                    "error": "Missing 'apiVersion' field"
                }
            
            if "kind" not in config_data or config_data.get("kind") != "Config":
                return {
                    "valid": False,
                    "error": "Invalid kind: expected 'Config'"
                }
            
            # Check for clusters, users, contexts
            if "clusters" not in config_data or not config_data.get("clusters"):
                return {
                    "valid": False,
                    "error": "No clusters defined in kubeconfig"
                }
            
            return {
                "valid": True,
                "clusters": len(config_data.get("clusters", [])),
                "contexts": len(config_data.get("contexts", [])),
                "users": len(config_data.get("users", []))
            }
            
        except yaml.YAMLError as e:
            return {
                "valid": False,
                "error": f"Invalid YAML format: {str(e)}"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }

