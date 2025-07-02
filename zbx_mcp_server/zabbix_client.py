"""Zabbix API client for host management operations."""

import json
from typing import Any, Dict, List, Optional
import httpx
from dataclasses import dataclass


@dataclass
class ZabbixConfig:
    """Zabbix instance configuration."""
    url: str
    username: str
    password: str
    timeout: int = 30
    verify_ssl: bool = True


class ZabbixAPIError(Exception):
    """Zabbix API error."""
    pass


class ZabbixClient:
    """Zabbix API client for host management."""
    
    def __init__(self, config: ZabbixConfig):
        self.config = config
        self.session_token: Optional[str] = None
        self.request_id = 1
        
    async def _make_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a JSON-RPC request to Zabbix API."""
        url = f"{self.config.url}/api_jsonrpc.php"
        
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_id
        }
        
        if self.session_token and method != "user.login":
            request_data["auth"] = self.session_token
            
        self.request_id += 1
        
        async with httpx.AsyncClient(
            timeout=self.config.timeout,
            verify=self.config.verify_ssl
        ) as client:
            try:
                response = await client.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                
                if "error" in result:
                    raise ZabbixAPIError(f"Zabbix API error: {result['error']}")
                    
                return result.get("result", {})
                
            except httpx.HTTPError as e:
                raise ZabbixAPIError(f"HTTP error: {str(e)}")
    
    async def login(self) -> str:
        """Login to Zabbix and get session token."""
        params = {
            "username": self.config.username,
            "password": self.config.password
        }
        
        result = await self._make_request("user.login", params)
        self.session_token = result
        return result
    
    async def logout(self) -> bool:
        """Logout from Zabbix."""
        if not self.session_token:
            return True
            
        try:
            await self._make_request("user.logout", {})
            self.session_token = None
            return True
        except ZabbixAPIError:
            return False
    
    async def get_hosts(
        self,
        group_name: Optional[str] = None,
        host_name: Optional[str] = None,
        status: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get hosts from Zabbix.
        
        Args:
            group_name: Filter by host group name
            host_name: Filter by host name (partial match)
            status: Host status (0=enabled, 1=disabled)
        
        Returns:
            List of host information
        """
        if not self.session_token:
            await self.login()
        
        params = {
            "output": ["hostid", "host", "name", "status", "available"],
            "selectGroups": ["groupid", "name"],
            "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type", "main"]
        }
        
        # Apply filters
        filter_params = {}
        if status is not None:
            filter_params["status"] = status
        if filter_params:
            params["filter"] = filter_params
        
        # Apply search
        search_params = {}
        if host_name:
            search_params["host"] = host_name
        if search_params:
            params["search"] = search_params
        
        # Apply group filter
        if group_name:
            # First get the group ID
            group_params = {
                "output": ["groupid"],
                "filter": {"name": group_name}
            }
            groups = await self._make_request("hostgroup.get", group_params)
            if groups:
                params["groupids"] = [group["groupid"] for group in groups]
            else:
                return []  # Group not found
        
        return await self._make_request("host.get", params)
    
    async def create_host(
        self,
        host_name: str,
        visible_name: str,
        group_ids: List[str],
        interfaces: List[Dict[str, Any]],
        templates: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new host.
        
        Args:
            host_name: Technical host name
            visible_name: Visible host name
            group_ids: List of host group IDs
            interfaces: List of host interfaces
            templates: List of template IDs (optional)
        
        Returns:
            Created host information
        """
        if not self.session_token:
            await self.login()
        
        params = {
            "host": host_name,
            "name": visible_name,
            "groups": [{"groupid": gid} for gid in group_ids],
            "interfaces": interfaces
        }
        
        if templates:
            params["templates"] = [{"templateid": tid} for tid in templates]
        
        return await self._make_request("host.create", params)
    
    async def update_host(
        self,
        host_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Update an existing host.
        
        Args:
            host_id: Host ID to update
            **kwargs: Fields to update
        
        Returns:
            Update result
        """
        if not self.session_token:
            await self.login()
        
        params = {"hostid": host_id, **kwargs}
        return await self._make_request("host.update", params)
    
    async def delete_host(self, host_ids: List[str]) -> Dict[str, Any]:
        """Delete hosts.
        
        Args:
            host_ids: List of host IDs to delete
        
        Returns:
            Delete result
        """
        if not self.session_token:
            await self.login()
        
        return await self._make_request("host.delete", host_ids)
    
    async def get_host_groups(self) -> List[Dict[str, Any]]:
        """Get all host groups."""
        if not self.session_token:
            await self.login()
        
        params = {
            "output": ["groupid", "name"]
        }
        
        return await self._make_request("hostgroup.get", params)
    
    async def get_templates(self) -> List[Dict[str, Any]]:
        """Get all templates."""
        if not self.session_token:
            await self.login()
        
        params = {
            "output": ["templateid", "host", "name"]
        }
        
        return await self._make_request("template.get", params)