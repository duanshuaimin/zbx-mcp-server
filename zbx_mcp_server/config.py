"""Configuration management for Zabbix MCP Server."""

import json
import os
from typing import Optional, Dict
from dataclasses import dataclass


@dataclass
class ZabbixServerConfig:
    """Zabbix server configuration."""
    url: str
    username: str
    password: str
    timeout: int = 30
    verify_ssl: bool = True
    name: Optional[str] = None
    description: Optional[str] = None
    max_retries: int = 1
    retry_backoff: float = 1.0


@dataclass
class ServerConfig:
    """MCP server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


@dataclass
class Config:
    """Main configuration."""
    zabbix_servers: Dict[str, ZabbixServerConfig]
    server: ServerConfig
    default_zabbix_server: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary for logging setup."""
        return {
            "log_level": self.server.log_level,
            "host": self.server.host,
            "port": self.server.port,
            "log_file": "logs/zabbix_mcp_server.log",
            "zabbix_log_file": "logs/zabbix_api.log"
        }


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file."""
    if config_path is None:
        for path in ["config.json", "../config.json", "./config.json"]:
            if os.path.exists(path):
                config_path = path
                break
        else:
            return Config(
                zabbix_servers={
                    "default": ZabbixServerConfig(
                        url="http://localhost:8080",
                        username="Admin",
                        password="zabbix",
                        verify_ssl=False,
                        name="Default Zabbix Server"
                    )
                },
                server=ServerConfig(),
                default_zabbix_server="default"
            )
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        server_config = ServerConfig(**data.get("server", {}))
        
        # Handle both old single-server and new multi-server formats
        if "zabbix" in data and isinstance(data["zabbix"], dict) and "url" in data["zabbix"]:
            # Old single-server format
            zabbix_config = ZabbixServerConfig(**data["zabbix"])
            if not zabbix_config.name:
                zabbix_config.name = "Default Server"
            
            return Config(
                zabbix_servers={"default": zabbix_config},
                server=server_config,
                default_zabbix_server="default"
            )
        
        elif "zabbix_servers" in data:
            # New multi-server format
            zabbix_servers = {}
            for server_id, server_data in data["zabbix_servers"].items():
                if not server_data.get("name"):
                    server_data["name"] = server_id.title()
                zabbix_servers[server_id] = ZabbixServerConfig(**server_data)
            
            default_server = data.get("default_zabbix_server")
            if default_server and default_server not in zabbix_servers:
                raise ValueError(f"Default server '{default_server}' not found in zabbix_servers")
            
            return Config(
                zabbix_servers=zabbix_servers,
                server=server_config,
                default_zabbix_server=default_server or next(iter(zabbix_servers.keys()))
            )
        else:
            raise KeyError("Neither 'zabbix' nor 'zabbix_servers' found in config")
        
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Failed to load config from {config_path}: {e}")


def get_server_config(config: Config, server_id: Optional[str] = None) -> ZabbixServerConfig:
    """Get configuration for a specific Zabbix server."""
    if server_id is None:
        server_id = config.default_zabbix_server
    
    if server_id not in config.zabbix_servers:
        available_servers = list(config.zabbix_servers.keys())
        raise ValueError(f"Server '{server_id}' not found. Available servers: {available_servers}")
    
    return config.zabbix_servers[server_id]


def list_servers(config: Config) -> Dict[str, str]:
    """List all configured Zabbix servers with their descriptions."""
    return {
        server_id: server_config.name or server_id
        for server_id, server_config in config.zabbix_servers.items()
    }