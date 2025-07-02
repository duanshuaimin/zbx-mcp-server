"""Minimal MCP server implementation."""

import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .models import (
    MCPRequest, MCPResponse, MCPError, InitializeResult, 
    ServerInfo, Tool, ListToolsResult, CallToolRequest, CallToolResult
)


class MCPServer:
    """Minimal MCP server."""
    
    def __init__(self):
        self.app = FastAPI(title="Zabbix MCP Server", version="0.1.0")
        self.setup_routes()
        self.tools = self._register_tools()
    
    def _register_tools(self) -> List[Tool]:
        """Register available tools."""
        return [
            Tool(
                name="echo",
                description="Echo back the input message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to echo back"
                        }
                    },
                    "required": ["message"]
                }
            ),
            Tool(
                name="ping",
                description="Simple ping tool that returns pong",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]
    
    def setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.post("/")
        async def handle_mcp_request(request: Request):
            """Handle MCP JSON-RPC requests."""
            try:
                body = await request.json()
                mcp_request = MCPRequest(**body)
                
                # Handle different MCP methods
                if mcp_request.method == "initialize":
                    result = self._handle_initialize(mcp_request)
                elif mcp_request.method == "tools/list":
                    result = self._handle_list_tools(mcp_request)
                elif mcp_request.method == "tools/call":
                    result = self._handle_call_tool(mcp_request)
                else:
                    result = self._create_error_response(
                        mcp_request.id, -32601, f"Method not found: {mcp_request.method}"
                    )
                
                return JSONResponse(content=result.model_dump())
                
            except Exception as e:
                error_response = MCPResponse(
                    id=None,
                    error=MCPError(code=-32603, message=f"Internal error: {str(e)}").model_dump()
                )
                return JSONResponse(content=error_response.model_dump())
    
    def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """Handle initialize method."""
        result = InitializeResult(
            protocolVersion="2024-11-05",
            capabilities={
                "tools": {}
            },
            serverInfo=ServerInfo(
                name="zbx-mcp-server",
                version="0.1.0"
            )
        )
        
        return MCPResponse(
            id=request.id,
            result=result.model_dump()
        )
    
    def _handle_list_tools(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/list method."""
        result = ListToolsResult(tools=self.tools)
        
        return MCPResponse(
            id=request.id,
            result=result.model_dump()
        )
    
    def _handle_call_tool(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/call method."""
        if not request.params:
            return self._create_error_response(
                request.id, -32602, "Missing params for tools/call"
            )
        
        try:
            tool_request = CallToolRequest(**request.params)
            
            # Execute the tool
            if tool_request.name == "echo":
                message = tool_request.arguments.get("message", "")
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": f"Echo: {message}"
                    }]
                )
            elif tool_request.name == "ping":
                result = CallToolResult(
                    content=[{
                        "type": "text", 
                        "text": "pong"
                    }]
                )
            else:
                return self._create_error_response(
                    request.id, -32602, f"Unknown tool: {tool_request.name}"
                )
            
            return MCPResponse(
                id=request.id,
                result=result.model_dump()
            )
            
        except Exception as e:
            return self._create_error_response(
                request.id, -32602, f"Invalid tool call: {str(e)}"
            )
    
    def _create_error_response(self, request_id: Optional[str], code: int, message: str) -> MCPResponse:
        """Create an error response."""
        return MCPResponse(
            id=request_id,
            error=MCPError(code=code, message=message).model_dump()
        )


def create_app() -> FastAPI:
    """Create and return the FastAPI app."""
    server = MCPServer()
    return server.app