"""Storage for security scan results."""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class SecurityScanStorage:
    """Manages storage of security scan results in ConfigMaps."""
    
    def __init__(self):
        """Initialize Kubernetes client."""
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            try:
                k8s_config.load_kube_config()
            except Exception as e:
                logger.warning(f"Could not load Kubernetes config: {e}")
        
        self.core_api = k8s_client.CoreV1Api()
        self.namespace = os.getenv("NAMESPACE", "sreagent")
    
    def _get_configmap_name(self, cluster_id: str) -> str:
        """Get ConfigMap name for a cluster's scan results."""
        return f"security-scan-{cluster_id}"
    
    def save_scan_result(
        self,
        cluster_id: str,
        scan_id: str,
        result: Dict[str, Any]
    ) -> bool:
        """Save scan result to ConfigMap."""
        configmap_name = self._get_configmap_name(cluster_id)
        
        try:
            # Get existing ConfigMap or create new
            try:
                configmap = self.core_api.read_namespaced_config_map(
                    name=configmap_name,
                    namespace=self.namespace,
                )
                data = json.loads(configmap.data.get("scans", "{}"))
            except ApiException as e:
                if e.status == 404:
                    # Create new ConfigMap
                    data = {}
                else:
                    raise
            
            # Add scan result
            data[scan_id] = result
            
            # Update ConfigMap
            body = {
                "data": {
                    "scans": json.dumps(data, indent=2),
                    "last_scan": scan_id,
                    "last_scan_time": result.get("timestamp", ""),
                }
            }
            
            try:
                self.core_api.patch_namespaced_config_map(
                    name=configmap_name,
                    namespace=self.namespace,
                    body=body,
                )
            except ApiException:
                # Create if doesn't exist
                metadata = {
                    "name": configmap_name,
                    "namespace": self.namespace,
                    "labels": {
                        "app": "cluster-inventory",
                        "component": "security-scanner",
                        "cluster-id": cluster_id,
                    },
                }
                body["metadata"] = metadata
                self.core_api.create_namespaced_config_map(
                    namespace=self.namespace,
                    body=body,
                )
            
            logger.info(f"Saved scan result {scan_id} for cluster {cluster_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save scan result: {e}", exc_info=True)
            return False
    
    def get_scan_results(
        self,
        cluster_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get scan results for a cluster."""
        configmap_name = self._get_configmap_name(cluster_id)
        
        try:
            configmap = self.core_api.read_namespaced_config_map(
                name=configmap_name,
                namespace=self.namespace,
            )
            data = json.loads(configmap.data.get("scans", "{}"))
            
            # Convert to list and sort by timestamp
            results = list(data.values())
            results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            if limit:
                results = results[:limit]
            
            return results
            
        except ApiException as e:
            if e.status == 404:
                return []
            raise
    
    def get_latest_scan_result(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest scan result for a cluster."""
        results = self.get_scan_results(cluster_id, limit=1)
        return results[0] if results else None

