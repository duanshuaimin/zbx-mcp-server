"""Integration tests for the MCP server."""

import pytest
from fastapi.testclient import TestClient
from zbx_mcp_server.server import create_app


class TestMCPServerIntegration:
    """Integration tests for the complete MCP server."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for integration tests."""
        app = create_app()
        return TestClient(app)
    
    def test_complete_mcp_workflow(self, client):
        """Test a complete MCP workflow: initialize -> list tools -> call tool."""
        # Step 1: Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        response = client.post("/", json=init_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "result" in data
        assert data["result"]["protocolVersion"] == "2024-11-05"
        assert data["result"]["serverInfo"]["name"] == "zbx-mcp-server"
        
        # Step 2: List tools
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = client.post("/", json=list_tools_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 2
        assert "result" in data
        assert len(data["result"]["tools"]) == 2
        
        # Step 3: Call echo tool
        call_echo_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": "Integration test message"}
            }
        }
        
        response = client.post("/", json=call_echo_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 3
        assert "result" in data
        assert data["result"]["content"][0]["text"] == "Echo: Integration test message"
        
        # Step 4: Call ping tool
        call_ping_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "ping",
                "arguments": {}
            }
        }
        
        response = client.post("/", json=call_ping_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 4
        assert "result" in data
        assert data["result"]["content"][0]["text"] == "pong"
    
    def test_error_handling_integration(self, client):
        """Test error handling in integration environment."""
        # Test unknown method
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown/method",
            "params": {}
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601
        
        # Test invalid JSON
        response = client.post(
            "/",
            content="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32603
    
    def test_tool_schema_validation(self, client):
        """Test that tool schemas are properly validated."""
        # Get tool list first to verify schemas
        list_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        response = client.post("/", json=list_request)
        data = response.json()
        
        tools = data["result"]["tools"]
        echo_tool = next(t for t in tools if t["name"] == "echo")
        ping_tool = next(t for t in tools if t["name"] == "ping")
        
        # Verify echo tool schema
        assert echo_tool["inputSchema"]["type"] == "object"
        assert "message" in echo_tool["inputSchema"]["properties"]
        assert echo_tool["inputSchema"]["required"] == ["message"]
        
        # Verify ping tool schema
        assert ping_tool["inputSchema"]["type"] == "object"
        assert ping_tool["inputSchema"]["required"] == []
    
    def test_request_response_correlation(self, client):
        """Test that request and response IDs are properly correlated."""
        test_cases = [
            {"id": "string_id", "expected_id": "string_id"},
            {"id": 42, "expected_id": 42},
            {"id": None, "expected_id": None},
        ]
        
        for case in test_cases:
            request_data = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {}
            }
            
            if case["id"] is not None:
                request_data["id"] = case["id"]
            
            response = client.post("/", json=request_data)
            data = response.json()
            
            assert data["id"] == case["expected_id"]


class TestMCPClientCompatibility:
    """Test compatibility with MCP client expectations."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for compatibility tests."""
        app = create_app()
        return TestClient(app)
    
    def test_mcp_protocol_compliance(self, client):
        """Test compliance with MCP protocol specifications."""
        # Test that all responses include jsonrpc field
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        response = client.post("/", json=request_data)
        data = response.json()
        
        assert "jsonrpc" in data
        assert data["jsonrpc"] == "2.0"
        assert "id" in data
        
        # Test capabilities format
        assert "result" in data
        result = data["result"]
        assert "protocolVersion" in result
        assert "capabilities" in result
        assert "serverInfo" in result
        
        # Test server info format
        server_info = result["serverInfo"]
        assert "name" in server_info
        assert "version" in server_info
    
    def test_tools_list_format(self, client):
        """Test that tools list follows expected format."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        response = client.post("/", json=request_data)
        data = response.json()
        
        assert "result" in data
        result = data["result"]
        assert "tools" in result
        assert isinstance(result["tools"], list)
        
        for tool in result["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert isinstance(tool["inputSchema"], dict)
    
    def test_tool_call_result_format(self, client):
        """Test that tool call results follow expected format."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": "test"}
            }
        }
        
        response = client.post("/", json=request_data)
        data = response.json()
        
        assert "result" in data
        result = data["result"]
        assert "content" in result
        assert "isError" in result
        assert isinstance(result["content"], list)
        assert isinstance(result["isError"], bool)
        
        for content_item in result["content"]:
            assert "type" in content_item


class TestMCPServerStability:
    """Test server stability and edge cases."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for stability tests."""
        app = create_app()
        return TestClient(app)
    
    def test_multiple_sequential_requests(self, client):
        """Test handling multiple sequential requests."""
        for i in range(10):
            request_data = {
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "echo",
                    "arguments": {"message": f"Message {i}"}
                }
            }
            
            response = client.post("/", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["id"] == i
            assert data["result"]["content"][0]["text"] == f"Echo: Message {i}"
    
    def test_edge_case_inputs(self, client):
        """Test edge case inputs."""
        # Empty message
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": ""}
            }
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["content"][0]["text"] == "Echo: "
        
        # Very long message
        long_message = "A" * 1000
        request_data = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": long_message}
            }
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["content"][0]["text"] == f"Echo: {long_message}"
    
    def test_malformed_requests(self, client):
        """Test handling of malformed requests."""
        # Missing required fields
        malformed_requests = [
            {"jsonrpc": "2.0", "id": 1},  # Missing method
            {"jsonrpc": "2.0", "method": "tools/call"},  # Missing params for tools/call
            {"id": 1, "method": "initialize"},  # Missing jsonrpc
        ]
        
        for request_data in malformed_requests:
            response = client.post("/", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert "error" in data