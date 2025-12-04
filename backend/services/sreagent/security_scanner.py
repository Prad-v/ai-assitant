"""Security scanner for Kubernetes clusters using AI agent analysis."""

import os
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.client.rest import ApiException

from .cluster_inventory_client import ClusterInventoryClient
from .agent import create_sre_agent
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

logger = logging.getLogger(__name__)

# Security scan prompt template
SECURITY_SCAN_PROMPT = """Perform a comprehensive security review of this Kubernetes cluster. 

Analyze all namespaces and identify security issues including:
1. Privileged containers
2. Containers running as root
3. Missing security contexts
4. Missing resource limits
5. Insecure image tags (:latest)
6. Secrets in environment variables
7. Missing network policies
8. Host namespace sharing
9. Excessive RBAC permissions
10. Missing Pod Security Standards

For each security issue found, provide:
- Severity (Critical, High, Medium, Low)
- Affected resources (namespace, resource type, resource name)
- Description of the issue
- Recommended Kyverno policy to fix it

Format your response as a structured security report with:
- Executive Summary: Overall security posture
- Findings: List of all security issues with severity
- Affected Resources: Detailed list of resources with issues
- Recommendations: Specific Kyverno policies for each issue
- Policy YAML: Complete Kyverno policy definitions ready to apply

Focus on the most critical security issues first. Use the MCP tools to inspect actual resource specs."""


class SecurityScanner:
    """Scans Kubernetes clusters for security issues using AI agent."""
    
    def __init__(self, cluster_inventory_service_url: Optional[str] = None):
        self.cluster_inventory_client = ClusterInventoryClient(
            base_url=cluster_inventory_service_url
        )
        self.scan_storage = SecurityScanStorage(
            cluster_inventory_service_url=cluster_inventory_service_url
        )
    
    async def scan_cluster_async(
        self,
        cluster_id: str,
        namespaces: Optional[List[str]] = None,
        scan_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform security scan on a cluster.
        
        Args:
            cluster_id: Cluster ID to scan
            namespaces: Optional list of namespaces to scan (None = all namespaces)
            scan_id: Optional scan ID (generated if not provided)
            
        Returns:
            Dictionary with scan results
        """
        if not scan_id:
            scan_id = str(uuid.uuid4())
        
        logger.info(f"Starting security scan {scan_id} for cluster {cluster_id}")
        
        # Get cluster info
        cluster = await self.cluster_inventory_client.get_cluster(cluster_id)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")
        
        # Get kubeconfig
        kubeconfig = await self.cluster_inventory_client.get_cluster_kubeconfig(cluster_id)
        if not kubeconfig:
            raise ValueError(f"Kubeconfig not found for cluster {cluster_id}")
        
        # Write kubeconfig to temp file and load it
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
            f.write(kubeconfig)
            temp_kubeconfig = f.name
        
        try:
            # Load kubeconfig
            k8s_config.load_kube_config(config_file=temp_kubeconfig)
            
            # Create agent with MCP tools for this cluster
            agent = create_sre_agent()
            session_service = InMemorySessionService()
            runner = Runner(
                agent=agent,
                app_name="security-scanner",
                session_service=session_service,
            )
            
            # Create scan session
            user_id = "security-scanner"
            session_id = f"scan-{scan_id}"
            
            # Create session (async)
            await session_service.create_session(
                app_name="security-scanner",
                user_id=user_id,
                session_id=session_id,
            )
            
            # Build scan prompt
            scan_prompt = SECURITY_SCAN_PROMPT
            if namespaces:
                scan_prompt += f"\n\nFocus on these namespaces: {', '.join(namespaces)}"
            else:
                scan_prompt += "\n\nScan all namespaces in the cluster."
            
            # Run security scan
            content = types.Content(
                role="user",
                parts=[types.Part(text=scan_prompt)],
            )
            
            # Collect agent response
            events = []
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
            ):
                events.append(event)
            
            # Extract response text from events
            response_text = ""
            for event in events:
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text'):
                                response_text += part.text
            
            # Parse scan results
            scan_result = self._parse_scan_results(response_text, cluster_id, scan_id)
            
            # Store scan results
            await self.scan_storage.save_scan_result(cluster_id, scan_id, scan_result)
            
            logger.info(f"Security scan {scan_id} completed for cluster {cluster_id}")
            
            return scan_result
            
        except Exception as e:
            logger.error(f"Security scan {scan_id} failed for cluster {cluster_id}: {e}", exc_info=True)
            error_result = {
                "scan_id": scan_id,
                "cluster_id": cluster_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self.scan_storage.save_scan_result(cluster_id, scan_id, error_result)
            raise
        
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_kubeconfig)
            except Exception:
                pass
    
    def _parse_scan_results(
        self,
        response_text: str,
        cluster_id: str,
        scan_id: str
    ) -> Dict[str, Any]:
        """Parse agent response into structured scan results."""
        # Try to extract structured information from the response
        # The agent should provide a structured report, but we'll parse it
        
        # Basic parsing - extract key sections
        findings = []
        recommendations = []
        policy_yaml = ""
        
        # Look for findings section
        if "Findings:" in response_text or "findings:" in response_text:
            # Try to extract findings
            # This is a simplified parser - in production, you might want more sophisticated parsing
            pass
        
        # Look for Kyverno policy YAML
        if "```yaml" in response_text:
            yaml_start = response_text.find("```yaml")
            yaml_end = response_text.find("```", yaml_start + 7)
            if yaml_end > yaml_start:
                policy_yaml = response_text[yaml_start + 7:yaml_end].strip()
        
        return {
            "scan_id": scan_id,
            "cluster_id": cluster_id,
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_response": response_text,
            "findings": findings,
            "recommendations": recommendations,
            "policy_yaml": policy_yaml,
            "summary": self._extract_summary(response_text),
        }
    
    def _extract_summary(self, response_text: str) -> str:
        """Extract executive summary from response."""
        # Look for summary section
        if "Executive Summary:" in response_text:
            summary_start = response_text.find("Executive Summary:")
            summary_end = response_text.find("\n\n", summary_start)
            if summary_end > summary_start:
                return response_text[summary_start:summary_end].strip()
        
        # Fallback: return first 500 characters
        return response_text[:500] + "..." if len(response_text) > 500 else response_text
    
    def scan_cluster(
        self,
        cluster_id: str,
        namespaces: Optional[List[str]] = None,
        scan_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for scan_cluster_async."""
        import asyncio
        return asyncio.run(
            self.scan_cluster_async(cluster_id, namespaces, scan_id)
        )
    
    async def scan_all_clusters_async(
        self,
        namespaces: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scan all registered clusters (async).
        
        Args:
            namespaces: Optional list of namespaces to scan per cluster
            
        Returns:
            List of scan results
        """
        clusters = await self.cluster_inventory_client.list_clusters()
        results = []
        
        for cluster in clusters:
            try:
                result = await self.scan_cluster_async(
                    cluster_id=cluster["id"],
                    namespaces=namespaces,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to scan cluster {cluster['id']}: {e}")
                results.append({
                    "cluster_id": cluster["id"],
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        
        return results
    
    def scan_all_clusters(
        self,
        namespaces: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for scan_all_clusters_async."""
        import asyncio
        return asyncio.run(
            self.scan_all_clusters_async(namespaces)
        )


class SecurityScanStorage:
    """Storage for security scan results via Cluster Inventory Service."""
    
    def __init__(self, cluster_inventory_service_url: Optional[str] = None):
        self.cluster_inventory_client = ClusterInventoryClient(
            base_url=cluster_inventory_service_url
        )
    
    async def save_scan_result(
        self,
        cluster_id: str,
        scan_id: str,
        result: Dict[str, Any]
    ):
        """Save scan result via Cluster Inventory Service."""
        try:
            await self.cluster_inventory_client.save_scan_result(
                cluster_id=cluster_id,
                scan_id=scan_id,
                result=result
            )
            logger.info(f"Saved scan result {scan_id} for cluster {cluster_id}")
        except Exception as e:
            logger.error(f"Failed to save scan result: {e}", exc_info=True)
            raise
    
    async def get_scan_results(
        self,
        cluster_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get scan results for a cluster via Cluster Inventory Service."""
        try:
            return await self.cluster_inventory_client.get_scan_results(
                cluster_id=cluster_id,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Failed to get scan results: {e}", exc_info=True)
            return []
    
    async def get_latest_scan(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest scan result for a cluster via Cluster Inventory Service."""
        try:
            return await self.cluster_inventory_client.get_latest_scan_result(cluster_id)
        except Exception as e:
            logger.error(f"Failed to get latest scan: {e}", exc_info=True)
            return None
    
    def save_scan_result_sync(
        self,
        cluster_id: str,
        scan_id: str,
        result: Dict[str, Any]
    ):
        """Synchronous wrapper for save_scan_result."""
        import asyncio
        return asyncio.run(self.save_scan_result(cluster_id, scan_id, result))
    
    def get_scan_results_sync(
        self,
        cluster_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_scan_results."""
        import asyncio
        return asyncio.run(self.get_scan_results(cluster_id, limit))
    
    def get_latest_scan_sync(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for get_latest_scan."""
        import asyncio
        return asyncio.run(self.get_latest_scan(cluster_id))

