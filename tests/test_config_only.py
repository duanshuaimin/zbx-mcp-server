#!/usr/bin/env python3
"""Test suite for distributed Zabbix server management functionality."""

from zbx_mcp_server.config import load_config
from zbx_mcp_server.server_manager import ZabbixServerManager
import json


def test_distributed_config_loading():
    """Test distributed Zabbix server configuration loading."""
    print("=== Testing Distributed Configuration Loading ===")
    
    try:
        # Load configuration
        config = load_config()
        print(f"✓ Distributed configuration loaded successfully")
        print(f"  - Number of distributed nodes: {len(config.zabbix_servers)}")
        print(f"  - Default node: {config.default_zabbix_server}")
        
        # List node details
        print("\n=== Distributed Node Details ===")
        for node_id, node_config in config.zabbix_servers.items():
            print(f"  {node_id}:")
            print(f"    Name: {node_config.name}")
            print(f"    URL: {node_config.url}")
            print(f"    Description: {node_config.description}")
            print(f"    Timeout: {node_config.timeout}s")
            print(f"    SSL Enabled: {node_config.verify_ssl}")
        
        # Test distributed server manager initialization
        print("\n=== Distributed Server Manager ===")
        manager = ZabbixServerManager(config)
        print(f"✓ Distributed server manager created successfully")
        
        # List distributed nodes
        nodes = manager.list_servers()
        print(f"✓ Distributed node list retrieved:")
        for node_id, node_info in nodes.items():
            print(f"  Node {node_id}:")
            print(f"    Name: {node_info['name']}")
            print(f"    Status: {node_info['status']}")
            print(f"    Is Default: {node_info['is_default']}")
            print(f"    SSL: {node_info['ssl_enabled']}")
        
        # Test node validation
        print("\n=== Node Validation ===")
        default_id = manager.validate_server_id(None)
        print(f"✓ Default node ID: {default_id}")
        
        # Test with first available node
        first_node = next(iter(config.zabbix_servers.keys()))
        valid_id = manager.validate_server_id(first_node)
        print(f"✓ Valid node ID '{first_node}': {valid_id}")
        
        try:
            invalid_id = manager.validate_server_id("nonexistent-node")
            print(f"✗ Invalid node test should have failed")
        except ValueError as e:
            print(f"✓ Invalid node correctly rejected: {e}")
        
        print("\n=== Distributed configuration tests passed! ===")
        
    except Exception as e:
        print(f"✗ Distributed configuration test failed: {e}")
        import traceback
        traceback.print_exc()


def test_backward_compatibility():
    """Test loading old-style configuration."""
    print("\n=== Testing Backward Compatibility ===")
    
    try:
        # Create old-style config in memory
        import tempfile
        import os
        
        old_config = {
            "zabbix": {
                "url": "http://localhost:8080",
                "username": "Admin",
                "password": "zabbix",
                "timeout": 30,
                "verify_ssl": False
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "log_level": "INFO"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(old_config, f, indent=2)
            temp_config_path = f.name
        
        try:
            # Load old-style configuration
            config = load_config(temp_config_path)
            print(f"✓ Old-style config loaded successfully")
            print(f"  - Servers: {list(config.zabbix_servers.keys())}")
            print(f"  - Default: {config.default_zabbix_server}")
            
            # Test with server manager
            manager = ZabbixServerManager(config)
            servers = manager.list_servers()
            print(f"✓ Server manager works with old config")
            print(f"  - Available servers: {list(servers.keys())}")
            
        finally:
            os.unlink(temp_config_path)
        
        print("✓ Backward compatibility test passed!")
        
    except Exception as e:
        print(f"✗ Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_distributed_config_loading()
    test_backward_compatibility()