# Zabbix MCP Server Tool Usage Guide

## Overview
This guide provides best practices for using Zabbix MCP Server tools to avoid unnecessary repeated calls and ensure efficient operation.

## General Principles

### 1. Single Call Pattern
- **All tools return complete results in a single call**
- **Do NOT call the same tool multiple times for the same query**
- Each tool is designed to provide comprehensive information immediately

### 2. Use Filters Wisely
- Only use filters when explicitly requested by the user
- Default behavior is to return all available data
- Filters should be used to narrow down results, not to explore data

## Tool-Specific Guidelines

### zabbix_get_hosts
**Purpose**: Get monitored hosts from a Zabbix server

**Best Practices**:
- Call once per query - results are complete
- Use `server_id` when targeting specific datacenter (e.g., 'datacenter-beijing')
- Only use filters when user specifically requests them:
  - `group_name`: When user mentions a specific group
  - `host_name`: When user asks for a specific host
  - `status`: When user asks for enabled/disabled hosts only
  - `include_templates`: When user asks for template information

**Example Usage**:
```json
// Get all hosts from Beijing datacenter
{
  "server_id": "datacenter-beijing"
}

// Get hosts from specific group (only when user mentions group)
{
  "server_id": "datacenter-beijing",
  "group_name": "Linux servers"
}
```

### zabbix_list_servers
**Purpose**: List all configured Zabbix servers

**Best Practices**:
- Call once to get complete server list
- No parameters needed
- Results include all server details

### zabbix_test_connection
**Purpose**: Test connectivity to Zabbix servers

**Best Practices**:
- Call once per test
- Results are immediate
- Use `server_id` for specific server, omit for all servers

### zabbix_get_server_info
**Purpose**: Get server information including version

**Best Practices**:
- Call once per server
- Results include version and status
- Use `server_id` for specific server

## Common Anti-Patterns to Avoid

### ❌ Repeated Calls
```
// BAD: Multiple calls for the same data
zabbix_get_hosts(server_id="datacenter-beijing")
zabbix_get_hosts(server_id="datacenter-beijing")
zabbix_get_hosts(server_id="datacenter-beijing")
```

### ❌ Unnecessary Filtering
```
// BAD: Using filters when not requested
zabbix_get_hosts(server_id="datacenter-beijing", status=0)
// When user just asked: "How many hosts are monitored?"
```

### ✅ Correct Usage
```
// GOOD: Single call with appropriate parameters
zabbix_get_hosts(server_id="datacenter-beijing")
// Then count the results in the response
```

## Error Handling

### Connection Issues
- Tools include built-in retry logic for network errors
- No need to retry failed calls manually
- Check server connectivity with `zabbix_test_connection` first

### Server Selection
- Use specific `server_id` when targeting particular datacenters
- Common server IDs:
  - `datacenter-beijing`: Beijing datacenter
  - `datacenter-shanghai`: Shanghai datacenter
  - Leave empty for default server

## Performance Optimization

### Retry Configuration
- Default retry count: 1 (reduced from 2)
- Only retries on network errors, not API errors
- Configurable via server configuration

### Logging
- All tool calls are logged with timing information
- Retry attempts are clearly marked
- Use logs to diagnose repeated call issues

## Configuration Examples

### Server Configuration
```json
{
  "zabbix_servers": {
    "datacenter-beijing": {
      "url": "http://zabbix-beijing.example.com",
      "username": "admin",
      "password": "password",
      "name": "Beijing Datacenter",
      "max_retries": 1,
      "retry_backoff": 1.0
    }
  }
}
```

## Troubleshooting

### If You See Repeated Calls
1. Check tool descriptions for single-call guidance
2. Verify you're not using unnecessary filters
3. Review logs for retry vs. new call patterns
4. Ensure proper error handling

### If Results Seem Incomplete
1. Verify server connectivity with `zabbix_test_connection`
2. Check server logs for API errors
3. Ensure proper authentication
4. Use `zabbix_get_server_info` to verify server status