"""Zabbix API client for host management operations."""

import json
import logging
import time
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
    
    def __init__(self, url: str = None, username: str = None, password: str = None, 
                 timeout: int = 30, verify_ssl: bool = True, config: ZabbixConfig = None):
        if config is not None:
            self.config = config
        else:
            self.config = ZabbixConfig(
                url=url,
                username=username,
                password=password,
                timeout=timeout,
                verify_ssl=verify_ssl
            )
        self.url = self.config.url
        self.session_token: Optional[str] = None
        self.request_id = 1
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = logging.getLogger(f"zabbix_client.{self.config.url}")
        
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in API requests/responses for logging."""
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                if key.lower() in ['password', 'token', 'sessionid']:
                    masked_data[key] = "***MASKED***"
                elif isinstance(value, dict):
                    masked_data[key] = self._mask_sensitive_data(value)
                elif isinstance(value, list):
                    masked_data[key] = [self._mask_sensitive_data(item) if isinstance(item, dict) else item for item in value]
                else:
                    masked_data[key] = value
            return masked_data
        return data
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                verify=self.config.verify_ssl
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self.session_token = None
    
    async def _make_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a JSON-RPC request to Zabbix API."""
        url = f"{self.config.url}/api_jsonrpc.php"
        
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_id
        }
        
        headers = {"Content-Type": "application/json"}
        
        # For authenticated requests, use Authorization Bearer header
        # Some methods like apiinfo.version should not include authorization header
        unauthenticated_methods = ["user.login", "apiinfo.version"]
        if self.session_token and method not in unauthenticated_methods:
            headers["Authorization"] = f"Bearer {self.session_token}"
            
        self.request_id += 1
        
        # Log request
        start_time = time.time()
        masked_request = self._mask_sensitive_data(request_data)
        self.logger.info(f"API Request: {method} - ID: {self.request_id-1}")
        self.logger.debug(f"Request URL: {url}")
        self.logger.debug(f"Request Data: {json.dumps(masked_request, indent=2)}")
        
        client = await self._get_client()
        try:
            response = await client.post(url, json=request_data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            # Log response
            duration = time.time() - start_time
            self.logger.info(f"API Response: {method} - ID: {self.request_id-1} - Duration: {duration:.3f}s - Status: {response.status_code}")
            
            if "error" in result:
                error_msg = f"Zabbix API error for method '{method}': {result['error']}"
                self.logger.error(f"API Error: {error_msg}")
                raise ZabbixAPIError(error_msg)
            
            # Log successful response (mask sensitive data)
            masked_result = self._mask_sensitive_data(result)
            self.logger.debug(f"Response Data: {json.dumps(masked_result, indent=2)}")
            
            return result.get("result", {})
            
        except httpx.HTTPError as e:
            duration = time.time() - start_time
            error_msg = f"HTTP error: {str(e)}"
            self.logger.error(f"API HTTP Error: {method} - ID: {self.request_id-1} - Duration: {duration:.3f}s - Error: {error_msg}")
            raise ZabbixAPIError(error_msg)
    
    async def login(self) -> str:
        """Login to Zabbix and get session token."""
        self.logger.info(f"Attempting login for user: {self.config.username}")
        params = {
            "username": self.config.username,
            "password": self.config.password
        }
        
        result = await self._make_request("user.login", params)
        self.session_token = result
        self.logger.info(f"Login successful for user: {self.config.username}")
        return result
    
    async def logout(self) -> bool:
        """Logout from Zabbix."""
        if not self.session_token:
            self.logger.debug("No session token, logout not needed")
            return True
            
        try:
            self.logger.info(f"Attempting logout for user: {self.config.username}")
            await self._make_request("user.logout", {})
            self.session_token = None
            self.logger.info(f"Logout successful for user: {self.config.username}")
            return True
        except ZabbixAPIError as e:
            self.logger.error(f"Logout failed for user: {self.config.username} - Error: {str(e)}")
            return False
    
    async def api_call(self, method: str, params: Dict[str, Any] = None) -> Any:
        """Make a generic API call to Zabbix."""
        if params is None:
            params = {}
        
        # Auto-login for authenticated methods
        if method != "user.login" and not self.session_token:
            self.logger.debug(f"Auto-login required for method: {method}")
            await self.login()
        
        return await self._make_request(method, params)
    
    async def get_hosts(
        self,
        group_name: Optional[str] = None,
        host_name: Optional[str] = None,
        status: Optional[int] = None,
        include_templates: bool = False
    ) -> List[Dict[str, Any]]:
        """Get hosts from Zabbix.
        
        Args:
            group_name: Filter by host group name
            host_name: Filter by host name (partial match)
            status: Host status (0=enabled, 1=disabled)
            include_templates: If True, include parent templates in the result.
        
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
        
        if include_templates:
            params["selectParentTemplates"] = ["templateid", "name"]
        
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