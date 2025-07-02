"""Configuration management for Zabbix MCP Server."""

import json
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class ZabbixServerConfig:
    """Zabbix server configuration."""
    url: str
    username: str
    password: str
    timeout: int = 30
    verify_ssl: bool = True


@dataclass
class ServerConfig:
    """MCP server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


@dataclass
class Config:
    """Main configuration."""
    zabbix: ZabbixServerConfig
    server: ServerConfig


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file."""
    if config_path is None:
        # Look for config.json in current directory or parent directory
        for path in ["config.json", "../config.json", "./config.json"]:
            if os.path.exists(path):
                config_path = path
                break
        else:
            # Use default configuration
            return Config(
                zabbix=ZabbixServerConfig(
                    url="http://localhost:8080",
                    username="Admin",
                    password="zabbix",
                    verify_ssl=False
                ),
                server=ServerConfig()
            )
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        zabbix_config = ZabbixServerConfig(**data["zabbix"])
        server_config = ServerConfig(**data.get("server", {}))
        
        return Config(zabbix=zabbix_config, server=server_config)
        
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Failed to load config from {config_path}: {e}")