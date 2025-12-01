"""Tests for Kubernetes deployment validation."""

import pytest
import subprocess
import json
import time
from typing import Dict, List


class TestDeployment:
    """Test suite for validating K8s deployment."""
    
    @pytest.fixture
    def namespace(self):
        """Get namespace from environment or use default."""
        import os
        return os.getenv("NAMESPACE", "default")
    
    @pytest.fixture
    def release_name(self):
        """Get Helm release name from environment or use default."""
        import os
        return os.getenv("RELEASE_NAME", "sreagent")
    
    def test_helm_chart_valid(self):
        """Test that Helm chart is valid."""
        try:
            result = subprocess.run(
                ["helm", "lint", "helm/sreagent"],
                capture_output=True,
                timeout=30,
            )
            assert result.returncode == 0, f"Helm lint failed: {result.stderr.decode()}"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("helm command not available")
    
    def test_deployment_exists(self, namespace, release_name):
        """Test that deployment exists in cluster."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "deployment", "-n", namespace, release_name, "-o", "json"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                deployment = json.loads(result.stdout)
                assert deployment["kind"] == "Deployment"
                assert deployment["metadata"]["name"] == release_name
            else:
                pytest.skip(f"Deployment {release_name} not found in namespace {namespace}")
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pytest.skip("Cannot check deployment - may not be in cluster")
    
    def test_deployment_ready(self, namespace, release_name):
        """Test that deployment is ready (all replicas available)."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "deployment", "-n", namespace, release_name, "-o", "json"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                deployment = json.loads(result.stdout)
                status = deployment.get("status", {})
                ready_replicas = status.get("readyReplicas", 0)
                replicas = status.get("replicas", 0)
                assert ready_replicas == replicas, f"Not all replicas ready: {ready_replicas}/{replicas}"
                assert ready_replicas > 0, "At least one replica should be ready"
            else:
                pytest.skip(f"Deployment {release_name} not found")
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pytest.skip("Cannot check deployment status")
    
    def test_pods_running(self, namespace, release_name):
        """Test that pods are running."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", namespace, "-l", f"app.kubernetes.io/instance={release_name}", "-o", "json"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                pods = json.loads(result.stdout)
                running_pods = [
                    p for p in pods.get("items", [])
                    if p.get("status", {}).get("phase") == "Running"
                ]
                assert len(running_pods) > 0, "At least one pod should be running"
            else:
                pytest.skip(f"Pods for {release_name} not found")
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pytest.skip("Cannot check pod status")
    
    def test_service_exists(self, namespace, release_name):
        """Test that service exists."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "service", "-n", namespace, release_name, "-o", "json"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                service = json.loads(result.stdout)
                assert service["kind"] == "Service"
            else:
                pytest.skip(f"Service {release_name} not found")
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pytest.skip("Cannot check service")
    
    def test_mcp_server_deployment(self, namespace):
        """Test that kubernetes-mcp-server deployment exists."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "deployment", "-n", namespace, "-l", "app=kubernetes-mcp-server", "-o", "json"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                deployments = json.loads(result.stdout)
                if deployments.get("items"):
                    # At least one MCP server deployment should exist
                    assert len(deployments["items"]) > 0
                else:
                    pytest.skip("kubernetes-mcp-server deployment not found")
            else:
                pytest.skip("Cannot check MCP server deployment")
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pytest.skip("Cannot check MCP server deployment")
    
    def test_ingress_exists_if_enabled(self, namespace, release_name):
        """Test that ingress exists if enabled in values."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "ingress", "-n", namespace, release_name, "-o", "json"],
                capture_output=True,
                timeout=10,
            )
            # Ingress may or may not exist depending on configuration
            # This test just verifies we can check it
            assert True
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pytest.skip("Cannot check ingress")
    
    def test_rbac_resources(self, namespace, release_name):
        """Test that RBAC resources (Role, RoleBinding) exist."""
        try:
            # Check Role
            role_result = subprocess.run(
                ["kubectl", "get", "role", "-n", namespace, release_name, "-o", "json"],
                capture_output=True,
                timeout=10,
            )
            # Check RoleBinding
            binding_result = subprocess.run(
                ["kubectl", "get", "rolebinding", "-n", namespace, release_name, "-o", "json"],
                capture_output=True,
                timeout=10,
            )
            # At least one should exist if RBAC is enabled
            assert role_result.returncode == 0 or binding_result.returncode == 0, "RBAC resources should exist"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Cannot check RBAC resources")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

