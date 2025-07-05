"""Tests for MCP server implementation."""

import json
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from zbx_mcp_server.server import MCPServer, create_app
from zbx_mcp_server.models import Tool


class TestMCPServer:
    """Test MCPServer class."""
    
    @pytest.fixture
    def server(self):
        """Create an MCPServer instance for testing."""
        return MCPServer()
    
    @pytest.fixture
    def client(self, server):
        """Create a test client for the server."""
        return TestClient(server.app)
    
    def test_server_initialization(self, server):
        """Test that server initializes correctly."""
        assert server.app is not None
        assert len(server.tools) == 14
        
        tool_names = [tool.name for tool in server.tools]
        assert "echo" in tool_names
        assert "ping" in tool_names
    
    def test_register_tools(self, server):
        """Test that tools are registered correctly."""
        tools = server._register_tools()
        assert len(tools) == 14
        
        echo_tool = next(t for t in tools if t.name == "echo")
        assert echo_tool.description == "Echo back the input message"
        assert "message" in echo_tool.inputSchema["properties"]
        assert echo_tool.inputSchema["required"] == ["message"]
        
        ping_tool = next(t for t in tools if t.name == "ping")
        assert ping_tool.description == "Simple ping tool that returns pong"
        assert ping_tool.inputSchema["required"] == []


class TestMCPEndpoints:
    """Test MCP HTTP endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        app = create_app()
        return TestClient(app)
    
    def test_initialize_method(self, client):
        """Test the initialize method."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "result" in data
        
        result = data["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert "capabilities" in result
        assert result["capabilities"]["tools"] == {}
        assert result["serverInfo"]["name"] == "zbx-mcp-server"
        assert result["serverInfo"]["version"] == "0.1.0"
    
    def test_list_tools_method(self, client):
        """Test the tools/list method."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 2
        assert "result" in data
        
        result = data["result"]
        assert "tools" in result
        assert len(result["tools"]) == 14
        
        tool_names = [tool["name"] for tool in result["tools"]]
        assert "echo" in tool_names
        assert "ping" in tool_names
    
    def test_call_echo_tool(self, client):
        """Test calling the echo tool."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": "Hello World"}
            }
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 3
        assert "result" in data
        
        result = data["result"]
        assert result["isError"] is False
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        assert result["content"][0]["text"] == "Echo: Hello World"
    
    def test_call_ping_tool(self, client):
        """Test calling the ping tool."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "ping",
                "arguments": {}
            }
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 4
        assert "result" in data
        
        result = data["result"]
        assert result["isError"] is False
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        assert result["content"][0]["text"] == "pong"
    
    def test_call_zabbix_get_problems_tool(self, client):
        """Test calling the zabbix_get_problems tool."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "zabbix_get_problems",
                "arguments": {}
            }
        }

        with patch("zbx_mcp_server.server_manager.ZabbixServerManager.execute_on_all_nodes", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"server1": {"data": [{"problem_id": "1", "name": "Test Problem"}]}}
            
            response = client.post("/", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == 10
            assert "result" in data
            
            result = data["result"]
            assert result["isError"] is False
            assert len(result["content"]) == 1
            assert result["content"][0]["type"] == "text"
            assert json.loads(result["content"][0]["text"]) == {"server1": {"data": [{"problem_id": "1", "name": "Test Problem"}]}}

    def test_unknown_method(self, client):
        """Test calling an unknown method."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "unknown/method",
            "params": {}
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 5
        assert "error" in data
        
        error = data["error"]
        assert error["code"] == -32601
        assert "Method not found" in error["message"]
    
    def test_unknown_tool(self, client):
        """Test calling an unknown tool."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {}
            }
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 6
        assert "error" in data
        
        error = data["error"]
        assert error["code"] == -32602
        assert "Unknown tool" in error["message"]
    
    def test_missing_params_for_tools_call(self, client):
        """Test calling tools/call without params."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call"
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 7
        assert "error" in data
        
        error = data["error"]
        assert error["code"] == -32602
        assert "Missing params" in error["message"]
    
    def test_invalid_json(self, client):
        """Test sending invalid JSON."""
        response = client.post("/", content="invalid json", headers={"content-type": "application/json"})
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "id" not in data
        assert "error" in data
        assert data["error"]["code"] == -32700
    
    def test_invalid_request_structure(self, client):
        """Test sending request with invalid structure."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 8
            # Missing method field
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32603
    
    def test_echo_with_missing_message(self, client):
        """Test calling echo tool without message parameter."""
        request_data = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {}
            }
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 9
        assert "result" in data
        
        result = data["result"]
        assert result["isError"] is False
        assert result["content"][0]["text"] == "Echo: "
    
    def test_request_without_id(self, client):
        """Test request without ID (notification)."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {}
        }
        
        response = client.post("/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "id" not in data
        assert "result" in data


class TestMCPServerInternals:
    """Test internal methods of MCPServer."""
    
    @pytest.fixture
    def server(self):
        """Create an MCPServer instance for testing."""
        return MCPServer()
    
    def test_create_error_response(self, server):
        """Test creating error responses."""
        error_response = server._create_error_response("test_id", -32601, "Test error")
        
        assert error_response.jsonrpc == "2.0"
        assert error_response.id == "test_id"
        assert error_response.result is None
        assert error_response.error is not None
        assert error_response.error["code"] == -32601
        assert error_response.error["message"] == "Test error"
    
    def test_create_error_response_no_id(self, server):
        """Test creating error response without ID."""
        error_response = server._create_error_response(None, -32600, "Invalid request")
        
        assert error_response.jsonrpc == "2.0"
        assert error_response.id is None
        assert error_response.error["code"] == -32600
        assert error_response.error["message"] == "Invalid request"


def test_create_app():
    """Test the create_app factory function."""
    app = create_app()
    assert app is not None
    assert app.title == "Zabbix MCP Server"
    assert app.version == "0.1.0"