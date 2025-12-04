"""HTTP client for Cluster Inventory Service."""

import os
import logging
from typing import Optional, Dict, List, Any
import httpx

logger = logging.getLogger(__name__)

# Default service URL (Kubernetes DNS)
DEFAULT_SERVICE_URL = os.getenv(
    "CLUSTER_INVENTORY_SERVICE_URL",
    "http://cluster-inventory:8001"
)


class ClusterInventoryClient:
    """HTTP client for communicating with Cluster Inventory Service."""
    
    def __init__(self, base_url: str = DEFAULT_SERVICE_URL):
        self.base_url = base_url.rstrip('/')
        self.timeout = 30.0
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
    
    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """Make HTTP request to cluster inventory service."""
        url = f"{self.base_url}{path}"
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                json=json_data,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from cluster inventory service: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Cluster inventory service error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error to cluster inventory service: {e}")
            raise Exception(f"Failed to connect to cluster inventory service: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error calling cluster inventory service: {e}")
            raise
    
    async def get_cluster(self, cluster_id: str) -> Optional[Dict]:
        """Get cluster details."""
        try:
            return await self._request("GET", f"/clusters/{cluster_id}")
        except Exception as e:
            logger.error(f"Failed to get cluster {cluster_id}: {e}")
            return None
    
    async def list_clusters(self) -> List[Dict]:
        """List all clusters."""
        try:
            result = await self._request("GET", "/clusters")
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Failed to list clusters: {e}")
            return []
    
    async def get_cluster_kubeconfig(self, cluster_id: str) -> Optional[str]:
        """Get kubeconfig for a cluster."""
        try:
            result = await self._request("GET", f"/clusters/{cluster_id}/kubeconfig")
            return result.get("kubeconfig") if result else None
        except Exception as e:
            logger.error(f"Failed to get kubeconfig for cluster {cluster_id}: {e}")
            return None
    
    async def test_cluster_connection(self, cluster_id: str) -> Dict:
        """Test cluster connection."""
        try:
            return await self._request("POST", f"/clusters/{cluster_id}/test")
        except Exception as e:
            logger.error(f"Failed to test connection for cluster {cluster_id}: {e}")
            return {
                "connected": False,
                "status": "error",
                "error": str(e)
            }
    
    async def get_cluster_info(self, cluster_id: str) -> Optional[Dict]:
        """Get detailed cluster information."""
        try:
            return await self._request("GET", f"/clusters/{cluster_id}/info")
        except Exception as e:
            logger.error(f"Failed to get cluster info for {cluster_id}: {e}")
            return None
    
    async def save_scan_result(
        self,
        cluster_id: str,
        scan_id: str,
        result: Dict[str, Any]
    ):
        """Save security scan result."""
        try:
            await self._request(
                "POST",
                f"/security/scans/{cluster_id}",
                json_data={"scan_id": scan_id, "result": result}
            )
        except Exception as e:
            logger.error(f"Failed to save scan result: {e}")
            raise
    
    async def get_scan_results(
        self,
        cluster_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get security scan results for a cluster."""
        try:
            params = {"limit": limit} if limit else None
            result = await self._request("GET", f"/security/scans/{cluster_id}", params=params)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Failed to get scan results: {e}")
            return []
    
    async def get_latest_scan_result(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest security scan result for a cluster."""
        try:
            return await self._request("GET", f"/security/scans/{cluster_id}/latest")
        except Exception as e:
            logger.error(f"Failed to get latest scan result: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

