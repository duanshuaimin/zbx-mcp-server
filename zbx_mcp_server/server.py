"""Minimal MCP server implementation."""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

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
                description="List all configured Zabbix servers with their details. Returns complete server list in a single call - do not call repeatedly.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="zabbix_test_connection",
                description="Test Zabbix server connectivity. Returns connection status for specified server or all servers. Call once per test - results are immediate.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Server ID to test (optional). If not specified, tests all configured servers. Use 'datacenter-beijing' for Beijing datacenter."
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_get_server_info",
                description="Get Zabbix server information including version and status. Returns immediate results - do not call multiple times for the same server.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Server ID (optional, defaults to first available server). Use 'datacenter-beijing' for Beijing datacenter."
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_get_hosts",
                description="Get monitored hosts from a Zabbix server. IMPORTANT: This tool returns complete results in a single call. Do NOT call this tool multiple times for the same query.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Zabbix server ID (optional, defaults to first available server). Use 'datacenter-beijing' for Beijing datacenter."
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
                name="zabbix_get_problems",
                description="Get current problems from a Zabbix server, or all Zabbix servers.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Zabbix server ID. If not specified, problems from all servers will be returned."
                        },
                        "sortfield": {
                            "type": "string",
                            "description": "Field to sort by (e.g., 'eventid', 'severity', 'clock')."
                        },
                        "sortorder": {
                            "type": "string",
                            "description": "Sort order ('ASC' or 'DESC')."
                        }
                    },
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
            ),
            Tool(
                name="zabbix_get_items",
                description="Get monitoring items from a Zabbix server.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Zabbix server ID (optional, defaults to first available server)."
                        },
                        "hostids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Host IDs to get items for."
                        },
                        "search": {
                            "type": "object",
                            "description": "Search parameters (e.g., {'name': 'CPU utilization'})."
                        },
                        "output": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields to return."
                        },
                        "sortfield": {
                            "type": "string",
                            "description": "Field to sort by (e.g., 'name', 'key_')."
                        },
                        "sortorder": {
                            "type": "string",
                            "description": "Sort order ('ASC' or 'DESC')."
                        }
                    },
                    "required": ["hostids"]
                }
            )
        ]
    
    def setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.post("/")
        async def handle_mcp_request(request: Request):
            """Handle MCP JSON-RPC requests."""
            body = None
            request_id = None
            try:
                body = await request.json()
                request_id = body.get("id") if isinstance(body, dict) else None

                if "jsonrpc" not in body:
                    raise ValueError("jsonrpc field is required")
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

            except ValidationError as e:
                error_response = self._create_error_response(
                    request_id, -32603, f"Invalid Request: {e.errors()[0]['msg']}"
                )
                return JSONResponse(content=error_response.model_dump())
            except json.JSONDecodeError:
                error_response = self._create_error_response(
                    None, -32700, "Parse error: Invalid JSON was received by the server."
                )
                return JSONResponse(content=error_response.model_dump())
            except Exception as e:
                error_response = self._create_error_response(
                    request_id, -32603, f"Invalid Request: {str(e)}"
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
                
                hosts = await client.get_hosts()
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
            elif tool_request.name == "zabbix_get_problems":
                server_id = tool_request.arguments.get("server_id")
                sortfield = tool_request.arguments.get("sortfield")
                sortorder = tool_request.arguments.get("sortorder")

                if server_id:
                    client = await self.server_manager.get_client(server_id)
                    problems = await client.get_problems(sortfield=sortfield, sortorder=sortorder)
                else:
                    problems = await self.server_manager.execute_on_all_nodes(
                        "problem.get", 
                        params={
                            "sortfield": sortfield,
                            "sortorder": sortorder,
                            "output": "extend",
                            "selectAcknowledges": "extend",
                            "selectTags": "extend",
                            "selectSuppressionData": "extend"
                        }
                    )

                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(problems, indent=2, ensure_ascii=False)
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
            elif tool_request.name == "zabbix_get_items":
                server_id = tool_request.arguments.get("server_id")
                hostids = tool_request.arguments.get("hostids")
                search = tool_request.arguments.get("search")
                output = tool_request.arguments.get("output")
                sortfield = tool_request.arguments.get("sortfield")
                sortorder = tool_request.arguments.get("sortorder")
                client = await self.server_manager.get_client(server_id)
                items = await client.get_items(
                    hostids=hostids,
                    search=search,
                    output=output,
                    sortfield=sortfield,
                    sortorder=sortorder
                )
                result = CallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(items, indent=2, ensure_ascii=False)
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