"""MCP protocol models."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel


class MCPRequest(BaseModel):
    """MCP request model."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """MCP response model."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class MCPError(BaseModel):
    """MCP error model."""
    code: int
    message: str
    data: Optional[Any] = None


class ServerInfo(BaseModel):
    """Server information model."""
    name: str
    version: str


class InitializeResult(BaseModel):
    """Initialize method result."""
    protocolVersion: str
    capabilities: Dict[str, Any]
    serverInfo: ServerInfo


class Tool(BaseModel):
    """Tool definition model."""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class ListToolsResult(BaseModel):
    """List tools result."""
    tools: List[Tool]


class CallToolRequest(BaseModel):
    """Call tool request."""
    name: str
    arguments: Dict[str, Any]


class CallToolResult(BaseModel):
    """Call tool result."""
    content: List[Dict[str, Any]]
    isError: bool = False