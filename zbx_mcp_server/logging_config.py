"""Logging configuration for Zabbix MCP Server."""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional, Dict, Any


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True
) -> None:
    """Setup logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        log_format: Custom log format (optional)
        max_file_size: Maximum log file size in bytes before rotation
        backup_count: Number of backup log files to keep
        enable_console: Whether to enable console logging
    """
    # Default log format
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def setup_zabbix_logging(config: Dict[str, Any]) -> None:
    """Setup logging specifically for Zabbix API operations.
    
    Args:
        config: Configuration dictionary containing logging settings
    """
    log_level = config.get("log_level", "INFO")
    log_file = config.get("log_file", "logs/zabbix_mcp_server.log")
    
    # Setup general logging
    setup_logging(
        log_level=log_level,
        log_file=log_file,
        enable_console=True
    )
    
    # Configure specific loggers
    zabbix_logger = logging.getLogger("zabbix_client")
    zabbix_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create dedicated Zabbix API log file
    zabbix_log_file = config.get("zabbix_log_file", "logs/zabbix_api.log")
    if zabbix_log_file:
        zabbix_path = Path(zabbix_log_file)
        zabbix_path.parent.mkdir(parents=True, exist_ok=True)
        
        zabbix_handler = logging.handlers.RotatingFileHandler(
            zabbix_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        zabbix_handler.setLevel(getattr(logging, log_level.upper()))
        zabbix_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        zabbix_handler.setFormatter(zabbix_formatter)
        zabbix_logger.addHandler(zabbix_handler)
    
    # Configure server manager logger
    server_manager_logger = logging.getLogger("server_manager")
    server_manager_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Configure MCP server logger
    mcp_logger = logging.getLogger("mcp_server")
    mcp_logger.setLevel(getattr(logging, log_level.upper()))


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)