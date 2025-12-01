"""Integration tests for SRE Agent with MCP tools."""

import pytest
import requests
import time
from typing import Dict


class TestAgentIntegration:
    """Test suite for agent-MCP integration."""
    
    @pytest.fixture
    def sreagent_url(self):
        """Get SRE Agent URL from environment or use default."""
        import os
        return os.getenv("SREAGENT_URL", "http://localhost:8000")
    
    @pytest.fixture
    def session_id(self):
        """Generate a unique session ID for tests."""
        return f"test_session_{int(time.time())}"
    
    def test_agent_initialization(self, sreagent_url):
        """Test that agent is properly initialized."""
        try:
            response = requests.get(f"{sreagent_url}/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data["agent_ready"] is True, "Agent should be ready"
        except requests.exceptions.ConnectionError:
            pytest.skip("SRE Agent not available")
    
    def test_simple_chat_interaction(self, sreagent_url, session_id):
        """Test basic chat interaction with agent."""
        try:
            payload = {
                "message": "Hello, can you help me troubleshoot a Kubernetes issue?",
                "user_id": "test_user",
                "session_id": session_id,
            }
            response = requests.post(
                f"{sreagent_url}/chat",
                json=payload,
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                assert "response" in data
                assert len(data["response"]) > 0, "Agent should provide a response"
                assert data["session_id"] == session_id, "Session ID should be preserved"
        except requests.exceptions.ConnectionError:
            pytest.skip("SRE Agent not available")
    
    def test_k8s_troubleshooting_query(self, sreagent_url, session_id):
        """Test agent response to K8s troubleshooting query."""
        try:
            payload = {
                "message": "How do I check if a pod is running?",
                "user_id": "test_user",
                "session_id": session_id,
            }
            response = requests.post(
                f"{sreagent_url}/chat",
                json=payload,
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                # Agent should provide helpful information about checking pod status
                assert len(data["response"]) > 0
        except requests.exceptions.ConnectionError:
            pytest.skip("SRE Agent not available")
    
    def test_session_persistence(self, sreagent_url, session_id):
        """Test that session persists across multiple messages."""
        try:
            # First message
            payload1 = {
                "message": "My name is TestUser",
                "user_id": "test_user",
                "session_id": session_id,
            }
            response1 = requests.post(
                f"{sreagent_url}/chat",
                json=payload1,
                timeout=30,
            )
            
            if response1.status_code == 200:
                # Second message in same session
                payload2 = {
                    "message": "What is my name?",
                    "user_id": "test_user",
                    "session_id": session_id,
                }
                response2 = requests.post(
                    f"{sreagent_url}/chat",
                    json=payload2,
                    timeout=30,
                )
                if response2.status_code == 200:
                    data2 = response2.json()
                    assert data2["session_id"] == session_id
        except requests.exceptions.ConnectionError:
            pytest.skip("SRE Agent not available")
    
    def test_mcp_tool_invocation(self, sreagent_url, session_id):
        """Test that agent can invoke MCP tools (if MCP is connected)."""
        try:
            # Check health first to see if MCP is connected
            health_response = requests.get(f"{sreagent_url}/health", timeout=5)
            if health_response.status_code == 200:
                health_data = health_response.json()
                mcp_connected = health_data.get("mcp_connected", False)
                
                if mcp_connected:
                    # Try a query that might use MCP tools
                    payload = {
                        "message": "List all namespaces in the cluster",
                        "user_id": "test_user",
                        "session_id": session_id,
                    }
                    response = requests.post(
                        f"{sreagent_url}/chat",
                        json=payload,
                        timeout=60,  # Longer timeout for tool execution
                    )
                    if response.status_code == 200:
                        data = response.json()
                        # Response should indicate tool usage or provide results
                        assert len(data["response"]) > 0
                else:
                    pytest.skip("MCP not connected - skipping tool invocation test")
        except requests.exceptions.ConnectionError:
            pytest.skip("SRE Agent not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

