"""Minimal MCP server implementation."""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .models import (
    MCPRequest, MCPResponse, MCPError, InitializeResult, 
    ServerInfo, Tool, ListToolsResult, CallToolRequest, CallToolResult
)
from .zabbix_client import ZabbixClient, ZabbixConfig
from .config import load_config
from .server_manager import ZabbixServerManager
from .logging_config import setup_zabbix_logging


class MCPServer:
    """Minimal MCP server."""
    
    def __init__(self, config_path: Optional[str] = None):
        # Load configuration first
        self.config = load_config(config_path)
        
        # Setup logging
        setup_zabbix_logging(self.config.to_dict())
        self.logger = logging.getLogger("mcp_server")
        
        self.app = FastAPI(title="Zabbix MCP Server", version="0.1.0")
        self.setup_routes()
        self.tools = self._register_tools()
        
        # Setup multi-server manager
        self.server_manager = ZabbixServerManager(self.config)
        self.logger.info("MCP Server initialized successfully")
    
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
                name="zabbix_list_servers",
                description="List configured Zabbix servers",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="zabbix_test_connection",
                description="Test Zabbix server connectivity. Call without parameters to test all servers.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Server ID to test (optional - defaults to testing all servers)"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_get_server_info",
                description="Get Zabbix server information. Call without parameters to get info from the first available server.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Server ID (optional - defaults to first available server)"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_get_hosts",
                description="Get monitored hosts from a Zabbix server. Call to get all hosts without parameters .  Use group_name, host_name, status, include_templates filters only when explicitly requested.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "optional - defaults to first available server，Zabbix server ID "
                        },
                        "group_name": {
                            "type": "string",
                            "description": "optional - only use when user specifically mentions a group，Host group name to filter by (exact match) "
                        },
                        "host_name": {
                            "type": "string", 
                            "description": "optional - only use when user specifies a hostname，Host name to search for (exact match)"
                        },
                        "status": {
                            "type": "integer",
                            "description": "optional - defaults to all hosts，Host status filter: 0=enabled, 1=disabled (optional)"
                        },
                        "include_templates": {
                            "type": "boolean",
                            "description": "optional - defaults to false，Include template info "
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_create_host",
                description="Create new monitored host",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "host_name": {
                            "type": "string",
                            "description": "Technical hostname (unique)"
                        },
                        "visible_name": {
                            "type": "string",
                            "description": "Display name"
                        },
                        "group_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Host group IDs"
                        },
                        "ip_address": {
                            "type": "string",
                            "description": "Host IP address"
                        },
                        "server_id": {
                            "type": "string",
                            "description": "Server ID (default: first available)"
                        },
                        "port": {
                            "type": "integer",
                            "description": "Agent port (default: 10050)"
                        }
                    },
                    "required": ["host_name", "visible_name", "group_ids", "ip_address"]
                }
            ),
            Tool(
                name="zabbix_update_host",
                description="Update existing host",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "host_id": {
                            "type": "string",
                            "description": "Host ID to update"
                        },
                        "host_name": {
                            "type": "string",
                            "description": "New hostname"
                        },
                        "visible_name": {
                            "type": "string",
                            "description": "New display name"
                        },
                        "status": {
                            "type": "integer",
                            "description": "Status: 0=enabled, 1=disabled"
                        },
                        "server_id": {
                            "type": "string",
                            "description": "Server ID (default: first available)"
                        }
                    },
                    "required": ["host_id"]
                }
            ),
            Tool(
                name="zabbix_delete_host",
                description="Delete hosts permanently",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "host_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Host IDs to delete"
                        },
                        "server_id": {
                            "type": "string",
                            "description": "Server ID (default: first available)"
                        }
                    },
                    "required": ["host_ids"]
                }
            ),
            Tool(
                name="zabbix_get_host_groups",
                description="Get all host groups from a Zabbix server. Call without parameters to get groups from the first available server. Only use when user explicitly asks for host groups list.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Server ID (optional - defaults to first available server)"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_get_templates",
                description="Get monitoring templates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Server ID (default: first available)"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_get_distributed_summary",
                description="Get health summary from all servers",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="zabbix_get_aggregated_hosts",
                description="Get hosts from all servers",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="zabbix_execute_on_all_nodes",
                description="Execute API call on all servers",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "Zabbix API method (e.g., 'host.get')"
                        },
                        "params": {
                            "type": "object",
                            "description": "API parameters (optional)"
                        }
                    },
                    "required": ["method"]
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
            elif tool_request.name == "zabbix_list_servers":
                servers = self.server_manager.list_servers()
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(servers, indent=2, ensure_ascii=False)
                    }]
                )
            elif tool_request.name == "zabbix_test_connection":
                server_id = tool_request.arguments.get("server_id")
                connection_results = await self.server_manager.test_connection(server_id)
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(connection_results, indent=2, ensure_ascii=False)
                    }]
                )
            elif tool_request.name == "zabbix_get_server_info":
                server_id = tool_request.arguments.get("server_id")
                server_info = await self.server_manager.get_server_info(server_id)
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(server_info, indent=2, ensure_ascii=False)
                    }]
                )
            elif tool_request.name == "zabbix_get_hosts":
                server_id = tool_request.arguments.get("server_id")
                client = await self.server_manager.get_client(server_id)
                hosts = await client.get_hosts(
                    group_name=tool_request.arguments.get("group_name"),
                    host_name=tool_request.arguments.get("host_name"),
                    status=tool_request.arguments.get("status"),
                    include_templates=tool_request.arguments.get("include_templates", False)
                )
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(hosts, indent=2, ensure_ascii=False)
                    }]
                )
            elif tool_request.name == "zabbix_create_host":
                args = tool_request.arguments
                server_id = args.pop("server_id", None)
                client = await self.server_manager.get_client(server_id)
                
                interfaces = [{
                    "type": 1,  # Zabbix agent
                    "main": 1,
                    "useip": 1,
                    "ip": args["ip_address"],
                    "dns": "",
                    "port": str(args.get("port", 10050))
                }]
                
                created_host = await client.create_host(
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
                server_id = args.pop("server_id", None)
                host_id = args.pop("host_id")
                client = await self.server_manager.get_client(server_id)
                
                updated_host = await client.update_host(host_id, **args)
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": f"Host updated successfully: {json.dumps(updated_host, indent=2)}"
                    }]
                )
            elif tool_request.name == "zabbix_delete_host":
                server_id = tool_request.arguments.get("server_id")
                host_ids = tool_request.arguments["host_ids"]
                client = await self.server_manager.get_client(server_id)
                deleted_hosts = await client.delete_host(host_ids)
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": f"Hosts deleted successfully: {json.dumps(deleted_hosts, indent=2)}"
                    }]
                )
            elif tool_request.name == "zabbix_get_host_groups":
                server_id = tool_request.arguments.get("server_id")
                client = await self.server_manager.get_client(server_id)
                groups = await client.get_host_groups()
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(groups, indent=2, ensure_ascii=False)
                    }]
                )
            elif tool_request.name == "zabbix_get_templates":
                server_id = tool_request.arguments.get("server_id")
                client = await self.server_manager.get_client(server_id)
                templates = await client.get_templates()
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(templates, indent=2, ensure_ascii=False)
                    }]
                )
            elif tool_request.name == "zabbix_get_distributed_summary":
                summary = await self.server_manager.get_distributed_summary()
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(summary, indent=2, ensure_ascii=False)
                    }]
                )
            elif tool_request.name == "zabbix_get_aggregated_hosts":
                aggregated_hosts = await self.server_manager.get_aggregated_hosts()
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(aggregated_hosts, indent=2, ensure_ascii=False)
                    }]
                )
            elif tool_request.name == "zabbix_execute_on_all_nodes":
                method = tool_request.arguments["method"]
                params = tool_request.arguments.get("params", {})
                execution_results = await self.server_manager.execute_on_all_nodes(method, params)
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(execution_results, indent=2, ensure_ascii=False)
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