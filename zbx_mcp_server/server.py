"""Minimal MCP server implementation."""

import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .models import (
    MCPRequest, MCPResponse, MCPError, InitializeResult, 
    ServerInfo, Tool, ListToolsResult, CallToolRequest, CallToolResult
)
from .zabbix_client import ZabbixClient, ZabbixConfig
from .config import load_config


class MCPServer:
    """Minimal MCP server."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.app = FastAPI(title="Zabbix MCP Server", version="0.1.0")
        self.setup_routes()
        self.tools = self._register_tools()
        
        # Load configuration
        self.config = load_config(config_path)
        self.zabbix_config = ZabbixConfig(
            url=self.config.zabbix.url,
            username=self.config.zabbix.username,
            password=self.config.zabbix.password,
            timeout=self.config.zabbix.timeout,
            verify_ssl=self.config.zabbix.verify_ssl
        )
        self.zabbix_client = ZabbixClient(self.zabbix_config)
    
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
            ),
            Tool(
                name="zabbix_get_hosts",
                description="Get hosts from Zabbix instance",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "group_name": {
                            "type": "string",
                            "description": "Filter by host group name (optional)"
                        },
                        "host_name": {
                            "type": "string", 
                            "description": "Filter by host name pattern (optional)"
                        },
                        "status": {
                            "type": "integer",
                            "description": "Host status: 0=enabled, 1=disabled (optional)"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_create_host",
                description="Create a new host in Zabbix",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "host_name": {
                            "type": "string",
                            "description": "Technical host name"
                        },
                        "visible_name": {
                            "type": "string",
                            "description": "Visible host name"
                        },
                        "group_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of host group IDs"
                        },
                        "ip_address": {
                            "type": "string",
                            "description": "Host IP address"
                        },
                        "port": {
                            "type": "integer",
                            "description": "Port number (default: 10050)"
                        }
                    },
                    "required": ["host_name", "visible_name", "group_ids", "ip_address"]
                }
            ),
            Tool(
                name="zabbix_update_host",
                description="Update an existing host in Zabbix",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "host_id": {
                            "type": "string",
                            "description": "Host ID to update"
                        },
                        "host_name": {
                            "type": "string",
                            "description": "New technical host name (optional)"
                        },
                        "visible_name": {
                            "type": "string",
                            "description": "New visible host name (optional)"
                        },
                        "status": {
                            "type": "integer",
                            "description": "New host status: 0=enabled, 1=disabled (optional)"
                        }
                    },
                    "required": ["host_id"]
                }
            ),
            Tool(
                name="zabbix_delete_host",
                description="Delete hosts from Zabbix",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "host_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of host IDs to delete"
                        }
                    },
                    "required": ["host_ids"]
                }
            ),
            Tool(
                name="zabbix_get_host_groups",
                description="Get all host groups from Zabbix",
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
                    result = await self._handle_call_tool(mcp_request)
                else:
                    result = self._create_error_response(
                        mcp_request.id, -32601, f"Method not found: {mcp_request.method}"
                    )
                
                return JSONResponse(content=result.model_dump())
                
            except Exception as e:
                error_response = MCPResponse(
                    id=getattr(body, 'id', None) if 'body' in locals() else None,
                    error={"code": -32603, "message": f"Internal error: {str(e)}"}
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
    
    async def _handle_call_tool(self, request: MCPRequest) -> MCPResponse:
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
            elif tool_request.name == "zabbix_get_hosts":
                hosts = await self.zabbix_client.get_hosts(
                    group_name=tool_request.arguments.get("group_name"),
                    host_name=tool_request.arguments.get("host_name"),
                    status=tool_request.arguments.get("status")
                )
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(hosts, indent=2, ensure_ascii=False)
                    }]
                )
            elif tool_request.name == "zabbix_create_host":
                args = tool_request.arguments
                interfaces = [{
                    "type": 1,  # Zabbix agent
                    "main": 1,
                    "useip": 1,
                    "ip": args["ip_address"],
                    "dns": "",
                    "port": str(args.get("port", 10050))
                }]
                
                created_host = await self.zabbix_client.create_host(
                    host_name=args["host_name"],
                    visible_name=args["visible_name"],
                    group_ids=args["group_ids"],
                    interfaces=interfaces
                )
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": f"Host created successfully: {json.dumps(created_host, indent=2)}"
                    }]
                )
            elif tool_request.name == "zabbix_update_host":
                args = tool_request.arguments
                host_id = args.pop("host_id")
                
                updated_host = await self.zabbix_client.update_host(host_id, **args)
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": f"Host updated successfully: {json.dumps(updated_host, indent=2)}"
                    }]
                )
            elif tool_request.name == "zabbix_delete_host":
                host_ids = tool_request.arguments["host_ids"]
                deleted_hosts = await self.zabbix_client.delete_host(host_ids)
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": f"Hosts deleted successfully: {json.dumps(deleted_hosts, indent=2)}"
                    }]
                )
            elif tool_request.name == "zabbix_get_host_groups":
                groups = await self.zabbix_client.get_host_groups()
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(groups, indent=2, ensure_ascii=False)
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
            error={"code": code, "message": message}
        )


def create_app(config_path: Optional[str] = None) -> FastAPI:
    """Create and return the FastAPI app."""
    server = MCPServer(config_path)
    return server.app