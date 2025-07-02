"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_mcp_request():
    """Sample MCP request for testing."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }


@pytest.fixture
def sample_tool_call_request():
    """Sample tool call request for testing."""
    return {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "echo",
            "arguments": {"message": "test message"}
        }
    }


@pytest.fixture
def sample_server_info():
    """Sample server info for testing."""
    return {
        "name": "test-server",
        "version": "1.0.0"
    }


@pytest.fixture
def sample_initialize_result():
    """Sample initialize result for testing."""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {
            "name": "test-server",
            "version": "1.0.0"
        }
    }


@pytest.fixture
def sample_tool_definition():
    """Sample tool definition for testing."""
    return {
        "name": "test_tool",
        "description": "A test tool",
        "inputSchema": {
            "type": "object",
            "properties": {
                "param1": {"type": "string"},
                "param2": {"type": "integer"}
            },
            "required": ["param1"]
        }
    }