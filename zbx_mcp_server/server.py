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
                description="List all configured Zabbix server nodes in the distributed infrastructure with their connection details",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="zabbix_test_connection",
                description="Test connectivity and authentication to specific Zabbix server nodes. Use without server_id to test ALL nodes at once and identify which nodes are reachable. Essential for diagnostics before attempting operations on specific nodes.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Target Zabbix server node ID to test. If omitted, tests all configured server nodes"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_get_server_info",
                description="Get detailed server information from ONE specific Zabbix node. Use this for targeted server diagnostics when you know the node is reachable. For distributed server overview, use zabbix_get_distributed_summary instead.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Target Zabbix server node ID. If omitted, uses the default configured server node"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_get_hosts",
                description="Retrieve host inventory from ONE specific Zabbix server node with optional filtering. Use this when you need data from a particular node that you know is operational. For comprehensive host data across all nodes, use zabbix_get_aggregated_hosts instead.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Target Zabbix server node ID. If omitted, queries the default configured server node"
                        },
                        "group_name": {
                            "type": "string",
                            "description": "Filter results to hosts belonging to this specific host group name"
                        },
                        "host_name": {
                            "type": "string", 
                            "description": "Filter results using partial host name matching (supports wildcards)"
                        },
                        "status": {
                            "type": "integer",
                            "description": "Filter by host monitoring status: 0=enabled/monitored, 1=disabled/not monitored"
                        },
                        "include_templates": {
                            "type": "boolean",
                            "description": "When true, include linked template information for each host in the response"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_create_host",
                description="Add a new monitored host to a specific Zabbix server node with required configuration (includes automatic retry up to 2 times)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Target Zabbix server node ID. If omitted, queries the default configured server node"
                        },
                        "host_name": {
                            "type": "string",
                            "description": "Technical hostname used internally by Zabbix (must be unique within the server)"
                        },
                        "visible_name": {
                            "type": "string",
                            "description": "Human-readable display name for the host (shown in Zabbix frontend)"
                        },
                        "group_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Array of host group IDs where this host will be placed (at least one required)"
                        },
                        "ip_address": {
                            "type": "string",
                            "description": "IP address of the host for Zabbix agent communication"
                        },
                        "port": {
                            "type": "integer",
                            "description": "TCP port number for Zabbix agent communication (default: 10050 if not specified)"
                        }
                    },
                    "required": ["host_name", "visible_name", "group_ids", "ip_address"]
                }
            ),
            Tool(
                name="zabbix_update_host",
                description="Modify configuration of an existing host on a specific Zabbix server node (includes automatic retry up to 2 times)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Target Zabbix server node ID. If omitted, queries the default configured server node"
                        },
                        "host_id": {
                            "type": "string",
                            "description": "Unique host ID of the existing host to be modified"
                        },
                        "host_name": {
                            "type": "string",
                            "description": "New technical hostname (must be unique within the server if provided)"
                        },
                        "visible_name": {
                            "type": "string",
                            "description": "New human-readable display name for the host"
                        },
                        "status": {
                            "type": "integer",
                            "description": "New monitoring status: 0=enable monitoring, 1=disable monitoring"
                        }
                    },
                    "required": ["host_id"]
                }
            ),
            Tool(
                name="zabbix_delete_host",
                description="Permanently remove one or more hosts from a specific Zabbix server node (includes automatic retry up to 2 times)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Target Zabbix server node ID. If omitted, queries the default configured server node"
                        },
                        "host_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Array of unique host IDs to be permanently deleted from the Zabbix server"
                        }
                    },
                    "required": ["host_ids"]
                }
            ),
            Tool(
                name="zabbix_get_host_groups",
                description="Retrieve all host groups and their details from a specific Zabbix server node (includes automatic retry up to 2 times)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Target Zabbix server node ID. If omitted, queries the default configured server node"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_get_templates",
                description="Retrieve all monitoring templates and their metadata from a specific Zabbix server node (includes automatic retry up to 2 times)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Target Zabbix server node ID. If omitted, queries the default configured server node"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="zabbix_get_distributed_summary",
                description="Smart aggregation of health status, version info, and key metrics from all configured Zabbix server nodes. Automatically skips unreachable nodes and provides partial results from available nodes. Use this when you need a complete overview regardless of individual node connectivity.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="zabbix_get_aggregated_hosts",
                description="Intelligent collection of host inventory from ALL available Zabbix server nodes. Gracefully handles connection failures by including only reachable nodes in the aggregated result. Ideal for getting a complete host inventory across your distributed infrastructure without manual node selection.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="zabbix_execute_on_all_nodes",
                description="Execute identical Zabbix API calls across ALL configured server nodes with intelligent error handling. Returns successful results from reachable nodes and clear error status for unreachable ones. Best choice for distributed operations when you want comprehensive coverage without manual node management.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "Zabbix API method name to execute (e.g., 'host.get', 'item.get', 'trigger.get')"
                        },
                        "params": {
                            "type": "object",
                            "description": "JSON parameters object for the specified Zabbix API method (structure depends on the method)"
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