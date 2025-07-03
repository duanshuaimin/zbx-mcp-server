#!/usr/bin/env python3
"""Test script for multi-server functionality."""

import asyncio
import json
from zbx_mcp_server.config import load_config
from zbx_mcp_server.server_manager import ZabbixServerManager


async def test_multi_server_configuration():
    """Test loading and using multi-server configuration."""
    print("=== Testing Multi-Server Configuration ===")
    
    # Load configuration
    config = load_config()
    print(f"Loaded {len(config.zabbix_servers)} servers:")
    
    for server_id, server_config in config.zabbix_servers.items():
        print(f"  - {server_id}: {server_config.name} ({server_config.url})")
    
    print(f"Default server: {config.default_zabbix_server}")
    
    # Test server manager
    manager = ZabbixServerManager(config)
    
    # List servers
    print("\n=== Server Manager - List Servers ===")
    servers = manager.list_servers()
    print(json.dumps(servers, indent=2))
    
    # Test connection to all servers
    print("\n=== Testing Connections ===")
    try:
        connection_results = await manager.test_connection()
        for server_id, success in connection_results.items():
            status = "✓ Connected" if success else "✗ Failed"
            server_name = config.zabbix_servers[server_id].name
            print(f"  {server_id} ({server_name}): {status}")
    except Exception as e:
        print(f"Connection test failed: {e}")
    
    # Test getting server info
    print("\n=== Getting Server Info ===")
    try:
        default_server_id = manager.get_default_server_id()
        server_info = await manager.get_server_info(default_server_id)
        print(f"Default server info:")
        print(json.dumps(server_info, indent=2))
    except Exception as e:
        print(f"Server info failed: {e}")
    
    # Test server validation
    print("\n=== Testing Server Validation ===")
    try:
        # Valid server
        valid_id = manager.validate_server_id("main")
        print(f"Valid server ID 'main' -> '{valid_id}'")
        
        # Default server (None)
        default_id = manager.validate_server_id(None)
        print(f"Default server ID (None) -> '{default_id}'")
        
        # Invalid server
        try:
            invalid_id = manager.validate_server_id("nonexistent")
            print(f"Invalid server test failed - should have thrown error")
        except ValueError as e:
            print(f"Invalid server ID 'nonexistent' -> Error: {e}")
            
    except Exception as e:
        print(f"Server validation test failed: {e}")
    
    # Clean up
    await manager.disconnect_all()
    print("\n=== Test Complete ===")


async def test_backward_compatibility():
    """Test backward compatibility with old single-server configuration."""
    print("\n=== Testing Backward Compatibility ===")
    
    # Create old-style config
    old_config = {
        "zabbix": {
            "url": "http://192.168.2.198",
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
    
    # Save temporary config file
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(old_config, f, indent=2)
        temp_config_path = f.name
    
    try:
        # Load old-style config
        from zbx_mcp_server.config import load_config
        config = load_config(temp_config_path)
        
        print(f"Loaded old-style config successfully:")
        print(f"  - Number of servers: {len(config.zabbix_servers)}")
        print(f"  - Default server: {config.default_zabbix_server}")
        print(f"  - Server names: {list(config.zabbix_servers.keys())}")
        
        # Verify it works with server manager
        manager = ZabbixServerManager(config)
        servers = manager.list_servers()
        print(f"  - Server manager works: {list(servers.keys())}")
        
        await manager.disconnect_all()
        print("Backward compatibility test passed!")
        
    finally:
        # Clean up temp file
        os.unlink(temp_config_path)


if __name__ == "__main__":
    asyncio.run(test_multi_server_configuration())
    asyncio.run(test_backward_compatibility())