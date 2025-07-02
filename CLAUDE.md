# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a minimal MCP (Model Context Protocol) server implementation using HTTP protocol. The server provides a basic JSON-RPC interface for MCP communication with simple tools.

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Or install in development mode with test dependencies
pip install -e .[test]
```

### Running the Server
```bash
# Simple run
python run.py

# With custom host/port
python -m zbx_mcp_server.main --host 0.0.0.0 --port 8080

# With auto-reload for development
python -m zbx_mcp_server.main --reload
```

### Testing the Server
```bash
# Test with curl (initialize)
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'

# List available tools
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# Call echo tool
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"echo","arguments":{"message":"Hello World"}}}'
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=zbx_mcp_server --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run tests using the test runner script
python test_runner.py
```

## Architecture

### Core Components
- `zbx_mcp_server/models.py` - Pydantic models for MCP protocol
- `zbx_mcp_server/server.py` - Main MCP server implementation with FastAPI
- `zbx_mcp_server/main.py` - CLI entry point with argument parsing

### MCP Protocol Support
- JSON-RPC 2.0 over HTTP
- Methods: `initialize`, `tools/list`, `tools/call`
- Built-in tools: `echo`, `ping`

### Project Structure
```
zbx_mcp_server/
├── __init__.py
├── models.py      # MCP protocol models
├── server.py      # FastAPI server implementation
└── main.py        # CLI entry point
```