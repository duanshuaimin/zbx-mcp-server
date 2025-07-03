"""Distributed Zabbix server management for MCP Server."""

from typing import Dict, Optional, List
import asyncio
import logging
from .zabbix_client import ZabbixClient
from .config import Config, ZabbixServerConfig, get_server_config


class ZabbixServerManager:
    """Manages distributed Zabbix server nodes and connections."""
    
    def __init__(self, config: Config):
        self.config = config
        self._clients: Dict[str, ZabbixClient] = {}
        self._client_locks: Dict[str, asyncio.Lock] = {}
        self.logger = logging.getLogger("server_manager")
    
    async def get_client(self, server_id: Optional[str] = None) -> ZabbixClient:
        """Get or create a Zabbix client for the specified server."""
        if server_id is None:
            server_id = self.config.default_zabbix_server
        
        if server_id not in self.config.zabbix_servers:
            available_servers = list(self.config.zabbix_servers.keys())
            error_msg = f"Server '{server_id}' not found. Available servers: {available_servers}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Create lock for this server if it doesn't exist
        if server_id not in self._client_locks:
            self._client_locks[server_id] = asyncio.Lock()
        
        async with self._client_locks[server_id]:
            if server_id not in self._clients:
                self.logger.info(f"Creating new Zabbix client for server: {server_id}")
                server_config = self.config.zabbix_servers[server_id]
                self._clients[server_id] = ZabbixClient(
                    url=server_config.url,
                    username=server_config.username,
                    password=server_config.password,
                    timeout=server_config.timeout,
                    verify_ssl=server_config.verify_ssl
                )
                self.logger.debug(f"Client created for server: {server_id} at {server_config.url}")
        
        return self._clients[server_id]
    
    def list_servers(self) -> Dict[str, Dict[str, str]]:
        """List all distributed Zabbix server nodes with their details."""
        servers = {}
        for server_id, server_config in self.config.zabbix_servers.items():
            servers[server_id] = {
                "node_id": server_id,
                "name": server_config.name or server_id,
                "url": server_config.url,
                "description": server_config.description or "",
                "is_default": server_id == self.config.default_zabbix_server,
                "status": "connected" if server_id in self._clients else "not_connected",
                "timeout": server_config.timeout,
                "ssl_enabled": server_config.verify_ssl
            }
        return servers
    
    async def test_connection(self, server_id: Optional[str] = None) -> Dict[str, bool]:
        """Test connection to a specific server or all servers."""
        results = {}
        
        if server_id:
            servers_to_test = [server_id]
        else:
            servers_to_test = list(self.config.zabbix_servers.keys())
        
        for sid in servers_to_test:
            try:
                client = await self.get_client(sid)
                # Try to make a simple API call to test the connection
                await client.api_call("apiinfo.version")
                results[sid] = True
            except Exception:
                results[sid] = False
        
        return results
    
    async def disconnect_server(self, server_id: str) -> bool:
        """Disconnect from a specific server."""
        if server_id in self._clients:
            try:
                client = self._clients[server_id]
                await client.close()
                del self._clients[server_id]
                return True
            except Exception:
                pass
        return False
    
    async def disconnect_all(self):
        """Disconnect from all servers."""
        for server_id in list(self._clients.keys()):
            await self.disconnect_server(server_id)
    
    async def get_server_info(self, server_id: Optional[str] = None) -> Dict[str, str]:
        """Get detailed information about a Zabbix server."""
        client = await self.get_client(server_id)
        
        try:
            version_info = await client.api_call("apiinfo.version")
            return {
                "server_id": server_id or self.config.default_zabbix_server,
                "version": version_info,
                "url": client.url,
                "status": "connected"
            }
        except Exception as e:
            return {
                "server_id": server_id or self.config.default_zabbix_server,
                "url": client.url,
                "status": "error",
                "error": str(e)
            }
    
    def get_default_server_id(self) -> str:
        """Get the default server ID."""
        return self.config.default_zabbix_server or next(iter(self.config.zabbix_servers.keys()))
    
    def validate_server_id(self, server_id: Optional[str]) -> str:
        """Validate and return a server ID, using default if None."""
        if server_id is None:
            return self.get_default_server_id()
        
        if server_id not in self.config.zabbix_servers:
            available_servers = list(self.config.zabbix_servers.keys())
            raise ValueError(f"Server '{server_id}' not found. Available servers: {available_servers}")
        
        return server_id
    
    async def get_distributed_summary(self) -> Dict[str, any]:
        """Get a summary of all distributed Zabbix server nodes."""
        summary = {
            "total_nodes": len(self.config.zabbix_servers),
            "default_node": self.config.default_zabbix_server,
            "nodes": {},
            "overall_status": "unknown"
        }
        
        connected_count = 0
        for server_id in self.config.zabbix_servers.keys():
            try:
                server_info = await self.get_server_info(server_id)
                summary["nodes"][server_id] = {
                    "status": "online",
                    "version": server_info.get("version", "unknown"),
                    "name": self.config.zabbix_servers[server_id].name
                }
                connected_count += 1
            except Exception as e:
                summary["nodes"][server_id] = {
                    "status": "offline", 
                    "error": str(e),
                    "name": self.config.zabbix_servers[server_id].name
                }
        
        if connected_count == len(self.config.zabbix_servers):
            summary["overall_status"] = "all_online"
        elif connected_count > 0:
            summary["overall_status"] = "partial_online"
        else:
            summary["overall_status"] = "all_offline"
        
        summary["connected_nodes"] = connected_count
        summary["offline_nodes"] = len(self.config.zabbix_servers) - connected_count
        
        return summary
    
    async def execute_on_all_nodes(self, method: str, params: Dict = None) -> Dict[str, any]:
        """Execute an API call on all distributed nodes and aggregate results."""
        if params is None:
            params = {}
        
        results = {}
        errors = {}
        
        for server_id in self.config.zabbix_servers.keys():
            try:
                client = await self.get_client(server_id)
                result = await client.api_call(method, params)
                results[server_id] = {
                    "status": "success",
                    "data": result,
                    "node_name": self.config.zabbix_servers[server_id].name
                }
            except Exception as e:
                errors[server_id] = {
                    "status": "error",
                    "error": str(e),
                    "node_name": self.config.zabbix_servers[server_id].name
                }
        
        return {
            "successful_nodes": results,
            "failed_nodes": errors,
            "total_nodes": len(self.config.zabbix_servers),
            "success_count": len(results),
            "failure_count": len(errors)
        }
    
    async def get_aggregated_hosts(self) -> Dict[str, any]:
        """Get hosts from all distributed nodes and aggregate them."""
        return await self.execute_on_all_nodes("host.get", {
            "output": ["hostid", "host", "name", "status"],
            "selectGroups": ["groupid", "name"]
        })