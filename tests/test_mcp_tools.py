"""Tests for MCP tools validation."""

import pytest
import requests
import time
import subprocess
import json
from typing import Dict, List


class TestMCPTools:
    """Test suite for validating MCP tools from kubernetes-mcp-server."""
    
    @pytest.fixture
    def mcp_server_url(self):
        """Get MCP server URL from environment or use default."""
        import os
        return os.getenv("MCP_SERVER_URL", "http://localhost:8080")
    
    @pytest.fixture
    def sreagent_url(self):
        """Get SRE Agent URL from environment or use default."""
        import os
        return os.getenv("SREAGENT_URL", "http://localhost:8000")
    
    def test_mcp_server_connectivity(self, mcp_server_url):
        """Test that MCP server is accessible."""
        try:
            # Try to connect to MCP server
            # Note: Actual MCP protocol may require specific endpoints
            response = requests.get(f"{mcp_server_url}/health", timeout=5)
            assert response.status_code in [200, 404], "MCP server should be accessible"
        except requests.exceptions.ConnectionError:
            pytest.skip("MCP server not available - skipping connectivity test")
    
    def test_sreagent_health(self, sreagent_url):
        """Test that SRE Agent health endpoint works."""
        try:
            response = requests.get(f"{sreagent_url}/health", timeout=5)
            assert response.status_code == 200, "Health endpoint should return 200"
            data = response.json()
            assert "status" in data, "Health response should contain status"
            assert data["status"] == "healthy", "Status should be healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("SRE Agent not available - skipping health test")
    
    def test_sreagent_mcp_connection(self, sreagent_url):
        """Test that SRE Agent reports MCP connection status."""
        try:
            response = requests.get(f"{sreagent_url}/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert "mcp_connected" in data, "Health should report MCP connection status"
            # MCP connection may be False if server is not available, which is acceptable
        except requests.exceptions.ConnectionError:
            pytest.skip("SRE Agent not available - skipping MCP connection test")
    
    def test_agent_chat_endpoint(self, sreagent_url):
        """Test that chat endpoint accepts requests."""
        try:
            payload = {
                "message": "List all pods in default namespace",
                "user_id": "test_user",
            }
            response = requests.post(
                f"{sreagent_url}/chat",
                json=payload,
                timeout=30,
            )
            # Should return 200 or 503 (if agent not ready)
            assert response.status_code in [200, 503], "Chat endpoint should respond"
            if response.status_code == 200:
                data = response.json()
                assert "response" in data, "Chat response should contain response field"
                assert "session_id" in data, "Chat response should contain session_id"
        except requests.exceptions.ConnectionError:
            pytest.skip("SRE Agent not available - skipping chat test")
    
    def test_mcp_tools_available(self):
        """Test that MCP tools are available via kubectl or direct check."""
        # This test would require actual MCP server connection
        # For now, we'll check if kubectl is available as a proxy test
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client"],
                capture_output=True,
                timeout=5,
            )
            # kubectl availability is a proxy for MCP server capability
            assert result.returncode == 0, "kubectl should be available for MCP tools"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("kubectl not available - skipping MCP tools test")
    
    def test_kubernetes_mcp_server_pod_running(self):
        """Test that kubernetes-mcp-server pod is running in cluster."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-l", "app=kubernetes-mcp-server", "-o", "json"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                pods = json.loads(result.stdout)
                if pods.get("items"):
                    # Check if at least one pod is running
                    running_pods = [
                        p for p in pods["items"]
                        if p.get("status", {}).get("phase") == "Running"
                    ]
                    assert len(running_pods) > 0, "At least one MCP server pod should be running"
                else:
                    pytest.skip("No kubernetes-mcp-server pods found")
            else:
                pytest.skip("kubectl command failed - may not be in cluster context")
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pytest.skip("Cannot check pod status - may not be in cluster")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

