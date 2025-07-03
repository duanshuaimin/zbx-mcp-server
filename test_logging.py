#!/usr/bin/env python3
"""Test script for Zabbix API logging functionality."""

import asyncio
import logging
from zbx_mcp_server.logging_config import setup_zabbix_logging
from zbx_mcp_server.config import load_config


async def test_logging():
    """Test the logging functionality."""
    # Load configuration
    config = load_config("config.json")
    
    # Setup logging
    setup_zabbix_logging(config.to_dict())
    
    # Test different loggers
    zabbix_logger = logging.getLogger("zabbix_client.test")
    server_logger = logging.getLogger("server_manager")
    mcp_logger = logging.getLogger("mcp_server")
    
    # Test log messages
    print("Testing Zabbix API logging...")
    
    zabbix_logger.info("Test Zabbix API info message")
    zabbix_logger.debug("Test Zabbix API debug message")
    zabbix_logger.warning("Test Zabbix API warning message")
    zabbix_logger.error("Test Zabbix API error message")
    
    server_logger.info("Test server manager info message")
    server_logger.debug("Test server manager debug message")
    
    mcp_logger.info("Test MCP server info message")
    mcp_logger.debug("Test MCP server debug message")
    
    print("Logging test completed. Check logs/ directory for output files.")


if __name__ == "__main__":
    asyncio.run(test_logging())