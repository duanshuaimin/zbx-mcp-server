"""Tests for MCP protocol models."""

import pytest
from pydantic import ValidationError
from zbx_mcp_server.models import (
    MCPRequest, MCPResponse, MCPError, ServerInfo, InitializeResult,
    Tool, ListToolsResult, CallToolRequest, CallToolResult
)


class TestMCPRequest:
    """Test MCPRequest model."""
    
    def test_valid_request(self):
        """Test creating a valid MCP request."""
        request = MCPRequest(
            id=1,
            method="initialize",
            params={"test": "value"}
        )
        assert request.jsonrpc == "2.0"
        assert request.id == 1
        assert request.method == "initialize"
        assert request.params == {"test": "value"}
    
    def test_minimal_request(self):
        """Test creating a minimal MCP request."""
        request = MCPRequest(method="ping")
        assert request.jsonrpc == "2.0"
        assert request.id is None
        assert request.method == "ping"
        assert request.params is None
    
    def test_missing_method(self):
        """Test that method is required."""
        with pytest.raises(ValidationError):
            MCPRequest()
    
    def test_dict_conversion(self):
        """Test converting request to dict."""
        request = MCPRequest(id="test", method="tools/list")
        request_dict = request.model_dump()
        expected = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/list",
            "params": None
        }
        assert request_dict == expected


class TestMCPResponse:
    """Test MCPResponse model."""
    
    def test_success_response(self):
        """Test creating a success response."""
        response = MCPResponse(
            id=1,
            result={"status": "ok"}
        )
        assert response.jsonrpc == "2.0"
        assert response.id == 1
        assert response.result == {"status": "ok"}
        assert response.error is None
    
    def test_error_response(self):
        """Test creating an error response."""
        response = MCPResponse(
            id=1,
            error={"code": -32601, "message": "Method not found"}
        )
        assert response.jsonrpc == "2.0"
        assert response.id == 1
        assert response.result is None
        assert response.error == {"code": -32601, "message": "Method not found"}
    
    def test_empty_response(self):
        """Test creating an empty response."""
        response = MCPResponse()
        assert response.jsonrpc == "2.0"
        assert response.id is None
        assert response.result is None
        assert response.error is None


class TestMCPError:
    """Test MCPError model."""
    
    def test_basic_error(self):
        """Test creating a basic error."""
        error = MCPError(code=-32601, message="Method not found")
        assert error.code == -32601
        assert error.message == "Method not found"
        assert error.data is None
    
    def test_error_with_data(self):
        """Test creating an error with additional data."""
        error = MCPError(
            code=-32602,
            message="Invalid params",
            data={"param": "missing"}
        )
        assert error.code == -32602
        assert error.message == "Invalid params"
        assert error.data == {"param": "missing"}
    
    def test_required_fields(self):
        """Test that code and message are required."""
        with pytest.raises(ValidationError):
            MCPError(code=-32601)
        
        with pytest.raises(ValidationError):
            MCPError(message="test")


class TestServerInfo:
    """Test ServerInfo model."""
    
    def test_server_info(self):
        """Test creating server info."""
        info = ServerInfo(name="test-server", version="1.0.0")
        assert info.name == "test-server"
        assert info.version == "1.0.0"
    
    def test_required_fields(self):
        """Test that name and version are required."""
        with pytest.raises(ValidationError):
            ServerInfo(name="test")
        
        with pytest.raises(ValidationError):
            ServerInfo(version="1.0.0")


class TestInitializeResult:
    """Test InitializeResult model."""
    
    def test_initialize_result(self):
        """Test creating initialize result."""
        server_info = ServerInfo(name="test", version="1.0.0")
        result = InitializeResult(
            protocolVersion="2024-11-05",
            capabilities={"tools": {}},
            serverInfo=server_info
        )
        assert result.protocolVersion == "2024-11-05"
        assert result.capabilities == {"tools": {}}
        assert result.serverInfo.name == "test"
        assert result.serverInfo.version == "1.0.0"
    
    def test_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            InitializeResult()


class TestTool:
    """Test Tool model."""
    
    def test_tool_creation(self):
        """Test creating a tool."""
        tool = Tool(
            name="echo",
            description="Echo tool",
            inputSchema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"]
            }
        )
        assert tool.name == "echo"
        assert tool.description == "Echo tool"
        assert tool.inputSchema["type"] == "object"
        assert "message" in tool.inputSchema["properties"]
    
    def test_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            Tool(name="test")


class TestListToolsResult:
    """Test ListToolsResult model."""
    
    def test_list_tools_result(self):
        """Test creating list tools result."""
        tools = [
            Tool(
                name="echo",
                description="Echo tool",
                inputSchema={"type": "object", "properties": {}}
            )
        ]
        result = ListToolsResult(tools=tools)
        assert len(result.tools) == 1
        assert result.tools[0].name == "echo"
    
    def test_empty_tools(self):
        """Test creating result with empty tools list."""
        result = ListToolsResult(tools=[])
        assert result.tools == []


class TestCallToolRequest:
    """Test CallToolRequest model."""
    
    def test_call_tool_request(self):
        """Test creating call tool request."""
        request = CallToolRequest(
            name="echo",
            arguments={"message": "hello"}
        )
        assert request.name == "echo"
        assert request.arguments == {"message": "hello"}
    
    def test_empty_arguments(self):
        """Test creating request with empty arguments."""
        request = CallToolRequest(name="ping", arguments={})
        assert request.name == "ping"
        assert request.arguments == {}
    
    def test_required_fields(self):
        """Test that name and arguments are required."""
        with pytest.raises(ValidationError):
            CallToolRequest(name="test")


class TestCallToolResult:
    """Test CallToolResult model."""
    
    def test_success_result(self):
        """Test creating a success result."""
        result = CallToolResult(
            content=[{"type": "text", "text": "Hello"}],
            isError=False
        )
        assert len(result.content) == 1
        assert result.content[0]["type"] == "text"
        assert result.content[0]["text"] == "Hello"
        assert result.isError is False
    
    def test_error_result(self):
        """Test creating an error result."""
        result = CallToolResult(
            content=[{"type": "text", "text": "Error occurred"}],
            isError=True
        )
        assert result.isError is True
        assert result.content[0]["text"] == "Error occurred"
    
    def test_default_is_error(self):
        """Test that isError defaults to False."""
        result = CallToolResult(content=[])
        assert result.isError is False
    
    def test_required_content(self):
        """Test that content is required."""
        with pytest.raises(ValidationError):
            CallToolResult()