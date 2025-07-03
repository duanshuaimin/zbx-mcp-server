# Zabbix MCP Server 远程主机测试手册

## 概述

本手册提供了完整的远程主机测试指南，包括 Zabbix MCP 服务器的配置、启动、API 调用测试以及日志监控等功能。

### 重要特性

- **分布式架构**: 支持多个 Zabbix 服务器节点的统一管理
- **自动重试机制**: 所有 Zabbix API 调用都包含自动重试功能，最多重试 2 次
- **指数退避**: 重试间隔采用指数退避策略（1秒、2秒）
- **智能重试**: 仅对网络错误和临时 API 错误进行重试，认证错误和方法错误不重试
- **详细日志**: 记录每次重试尝试和最终结果
- **清晰语义**: 工具描述明确区分单节点操作和跨节点聚合操作

## 1. 服务器配置

### 1.1 基本配置文件 (config.json)

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "log_level": "INFO"
  },
  "zabbix_servers": {
    "datacenter-beijing": {
      "name": "Production Beijing Datacenter",
      "url": "http://your-zabbix-server:80/zabbix",
      "username": "Admin",
      "password": "your-password",
      "timeout": 30,
      "verify_ssl": false
    },
    "datacenter-shanghai": {
      "name": "Production Shanghai Datacenter", 
      "url": "http://your-zabbix-server2:80/zabbix",
      "username": "Admin",
      "password": "your-password",
      "timeout": 30,
      "verify_ssl": false
    }
  },
  "default_zabbix_server": "datacenter-beijing"
}
```

### 1.2 日志级别配置

支持的日志级别：
- `DEBUG`: 详细的调试信息，包括完整的 API 请求和响应
- `INFO`: 基本的操作信息，包括登录、API 调用等
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误信息

## 2. 服务器启动

### 2.1 基本启动

```bash
# 使用默认配置启动
python -m zbx_mcp_server.main

# 指定配置文件
python -m zbx_mcp_server.main --config /path/to/config.json

# 指定主机和端口
python -m zbx_mcp_server.main --host 0.0.0.0 --port 8080

# 开启开发模式（自动重载）
python -m zbx_mcp_server.main --reload
```

### 2.2 日志输出

服务器启动后，日志将输出到以下位置：
- 控制台：实时显示 INFO 级别以上的日志
- `logs/zabbix_mcp_server.log`: 主服务器日志
- `logs/zabbix_api.log`: Zabbix API 专用日志

## 3. MCP 工具语义说明

### 3.1 智能工具选择指南

Zabbix MCP 服务器提供了不同层次的工具，根据您的需求智能选择：

#### 🎯 单节点精准操作工具（前缀：`zabbix_`）
- **使用场景**: 当您明确知道目标节点且确认其可用时
- **特点**: 针对特定节点，连接失败时直接报错
- **最佳实践**: 先用 `zabbix_test_connection` 确认节点可达性
- **示例**: `zabbix_get_hosts`, `zabbix_create_host`

#### 🌐 智能聚合工具（前缀：`zabbix_get_aggregated_` 或 `zabbix_get_distributed_`）
- **使用场景**: 需要从所有可用节点获取数据，不关心个别节点的连接状态
- **特点**: 自动跳过不可达节点，返回可用节点的聚合结果
- **优势**: 容错性强，适合分布式环境中的数据收集
- **示例**: `zabbix_get_aggregated_hosts`, `zabbix_get_distributed_summary`

#### ⚡ 全节点执行工具（前缀：`zabbix_execute_on_all_`）
- **使用场景**: 需要在所有节点执行相同操作并查看每个节点的独立结果
- **特点**: 返回每个节点的详细执行状态（成功/失败）
- **用途**: 批量配置、状态检查、性能分析
- **示例**: `zabbix_execute_on_all_nodes`

#### 💡 工具选择建议

**统计监控主机** → 使用 `zabbix_get_aggregated_hosts`
- ✅ 自动聚合所有可用节点的主机数据
- ✅ 忽略连接失败的节点
- ❌ 避免使用单节点工具逐个查询

**检查系统状态** → 使用 `zabbix_get_distributed_summary`
- ✅ 一次性获取所有节点的健康状态
- ✅ 包含连接失败节点的错误信息

**创建/修改主机** → 使用单节点工具 `zabbix_create_host`
- ✅ 精确控制在哪个节点操作
- ⚠️ 操作前建议先测试连接

### 3.2 参数语义规范

- **server_id**: "目标 Zabbix 服务器节点 ID"，明确指定操作的目标节点
- **host_id**: "唯一主机 ID"，用于标识具体的主机记录
- **group_ids**: "主机组 ID 数组"，明确表示需要提供数组格式
- **include_templates**: "包含模板信息"，布尔值控制返回数据的详细程度

## 4. API 测试

### 4.1 初始化连接

```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {}
  }'
```

预期响应：
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "0.1.0",
    "serverInfo": {
      "name": "Zabbix MCP Server",
      "version": "0.1.0"
    }
  }
}
```

### 4.2 列出可用工具

```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
```

### 4.3 测试 Zabbix 服务器连接

```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "test_zabbix_connection",
      "arguments": {
        "server_id": "datacenter-beijing"
      }
    }
  }'
```

### 4.4 获取主机列表

```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "get_hosts",
      "arguments": {
        "server_id": "datacenter-beijing",
        "status": 0
      }
    }
  }'
```

### 4.5 分布式服务器概览

```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "distributed_summary",
      "arguments": {}
    }
  }'
```

## 4. 日志监控

### 4.1 实时日志监控

```bash
# 监控主服务器日志
tail -f logs/zabbix_mcp_server.log

# 监控 API 日志
tail -f logs/zabbix_api.log

# 同时监控两个日志文件
tail -f logs/zabbix_mcp_server.log logs/zabbix_api.log
```

### 4.2 日志格式说明

#### API 请求日志
```
2025-07-03 14:37:37,434 - zabbix_client.http://zabbix-server/zabbix - INFO - API Request: user.login - ID: 1
2025-07-03 14:37:37,434 - zabbix_client.http://zabbix-server/zabbix - DEBUG - Request URL: http://zabbix-server/zabbix/api_jsonrpc.php
2025-07-03 14:37:37,434 - zabbix_client.http://zabbix-server/zabbix - DEBUG - Request Data: {"jsonrpc": "2.0", "method": "user.login", "params": {"username": "Admin", "password": "***MASKED***"}, "id": 1}
```

#### API 重试日志
```
2025-07-03 14:37:37,434 - zabbix_client.http://zabbix-server/zabbix - WARNING - API HTTP Error (retry 1/2): host.get - ID: 2 - Duration: 5.000s - Error: HTTP error: timeout
2025-07-03 14:37:39,434 - zabbix_client.http://zabbix-server/zabbix - INFO - API Request Retry 2/2: host.get - ID: 2
```

#### API 响应日志
```
2025-07-03 14:37:37,634 - zabbix_client.http://zabbix-server/zabbix - INFO - API Response: user.login - ID: 1 - Duration: 0.200s - Status: 200
2025-07-03 14:37:37,634 - zabbix_client.http://zabbix-server/zabbix - DEBUG - Response Data: {"jsonrpc": "2.0", "result": "***MASKED***", "id": 1}
```

#### 错误日志
```
2025-07-03 14:37:37,734 - zabbix_client.http://zabbix-server/zabbix - ERROR - API Error: Zabbix API error for method 'host.get': {"code": -32602, "message": "Invalid params.", "data": "Invalid parameter \"/\": value is expected."}
```

## 5. 常见测试场景

### 5.1 连接测试

**测试目标**: 验证与所有配置的 Zabbix 服务器的连接

```bash
# 测试默认服务器
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "test_zabbix_connection",
      "arguments": {}
    }
  }'

# 测试指定服务器
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "test_zabbix_connection",
      "arguments": {
        "server_id": "datacenter-shanghai"
      }
    }
  }'
```

**预期日志输出**:
```
2025-07-03 14:37:37,434 - server_manager - INFO - Creating new Zabbix client for server: datacenter-beijing
2025-07-03 14:37:37,434 - zabbix_client.http://zabbix-server/zabbix - INFO - Attempting login for user: Admin
2025-07-03 14:37:37,434 - zabbix_client.http://zabbix-server/zabbix - INFO - API Request: user.login - ID: 1
2025-07-03 14:37:37,634 - zabbix_client.http://zabbix-server/zabbix - INFO - API Response: user.login - ID: 1 - Duration: 0.200s - Status: 200
2025-07-03 14:37:37,634 - zabbix_client.http://zabbix-server/zabbix - INFO - Login successful for user: Admin
```

### 5.2 主机管理测试

**测试目标**: 验证主机的 CRUD 操作

```bash
# 获取主机列表
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "get_hosts",
      "arguments": {
        "server_id": "datacenter-beijing",
        "host_name": "test",
        "status": 0
      }
    }
  }'

# 创建主机
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "create_host",
      "arguments": {
        "server_id": "datacenter-beijing",
        "host_name": "test-host-01",
        "visible_name": "Test Host 01",
        "group_ids": ["2"],
        "interfaces": [{
          "type": 1,
          "main": 1,
          "useip": 1,
          "ip": "192.168.1.100",
          "dns": "",
          "port": "10050"
        }]
      }
    }
  }'
```

### 5.3 分布式操作测试

**测试目标**: 验证跨多个 Zabbix 服务器的操作

```bash
# 获取所有服务器的汇总信息
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "distributed_summary",
      "arguments": {}
    }
  }'

# 在所有服务器上执行 API 调用
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 6,
    "method": "tools/call",
    "params": {
      "name": "distributed_api_call",
      "arguments": {
        "method": "host.get",
        "params": {
          "output": ["hostid", "host", "name"],
          "limit": 5
        }
      }
    }
  }'
```

## 6. 性能测试

### 6.1 并发连接测试

```bash
# 使用 Apache Bench 进行并发测试
ab -n 100 -c 10 -p test_request.json -T application/json http://localhost:8000/

# test_request.json 内容
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "ping",
    "arguments": {}
  }
}
```

### 6.2 日志分析

```bash
# 分析 API 响应时间
grep "Duration:" logs/zabbix_api.log | awk '{print $10}' | sort -n

# 统计 API 调用次数
grep "API Request:" logs/zabbix_api.log | wc -l

# 查找错误
grep "ERROR" logs/zabbix_mcp_server.log
```

## 7. 故障排除

### 7.1 常见问题

#### 连接失败
- 检查 Zabbix 服务器 URL 是否正确
- 验证用户名和密码
- 检查网络连接和防火墙设置

#### 认证失败
- 确认 Zabbix 用户权限
- 检查 API 访问权限
- 验证 Zabbix 版本兼容性

#### 日志不输出
- 检查日志级别设置
- 确认 logs 目录存在且有写权限
- 验证日志配置

### 7.2 调试模式

```bash
# 启用调试模式
python -m zbx_mcp_server.main --config config.json

# 修改配置文件中的日志级别为 DEBUG
{
  "server": {
    "log_level": "DEBUG"
  }
}
```

### 7.3 日志轮转

日志文件会自动轮转，默认配置：
- 最大文件大小：10MB
- 保留备份数：5个
- 轮转后的文件名：`zabbix_mcp_server.log.1`, `zabbix_mcp_server.log.2`, 等

## 8. 最佳实践

### 8.1 生产环境配置

1. **安全设置**:
   - 启用 SSL 验证
   - 使用强密码
   - 限制网络访问

2. **日志管理**:
   - 设置合适的日志级别（生产环境建议 INFO）
   - 定期清理旧日志
   - 监控日志文件大小

3. **性能优化**:
   - 调整连接超时时间
   - 配置连接池大小
   - 监控 API 响应时间

### 8.2 监控建议

1. **关键指标**:
   - API 响应时间
   - 错误率
   - 并发连接数
   - 内存使用情况

2. **告警设置**:
   - API 调用失败率过高
   - 响应时间过长
   - 连接超时

## 9. 示例脚本

### 9.1 自动化测试脚本

```python
#!/usr/bin/env python3
"""Zabbix MCP Server 自动化测试脚本"""

import asyncio
import json
import aiohttp
from datetime import datetime

class ZabbixMCPTester:
    def __init__(self, server_url="http://localhost:8000"):
        self.server_url = server_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def call_method(self, method, params=None):
        """调用 MCP 方法"""
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        async with self.session.post(
            self.server_url,
            json=request_data,
            headers={"Content-Type": "application/json"}
        ) as response:
            return await response.json()
    
    async def test_connection(self):
        """测试连接"""
        print("Testing connection...")
        result = await self.call_method("initialize")
        print(f"Initialize result: {result}")
        
    async def test_tools_list(self):
        """测试工具列表"""
        print("Testing tools list...")
        result = await self.call_method("tools/list")
        print(f"Available tools: {len(result.get('result', {}).get('tools', []))}")
        
    async def test_zabbix_connection(self):
        """测试 Zabbix 连接"""
        print("Testing Zabbix connection...")
        result = await self.call_method("tools/call", {
            "name": "test_zabbix_connection",
            "arguments": {}
        })
        print(f"Zabbix connection result: {result}")

async def main():
    async with ZabbixMCPTester() as tester:
        await tester.test_connection()
        await tester.test_tools_list()
        await tester.test_zabbix_connection()

if __name__ == "__main__":
    asyncio.run(main())
```

### 9.2 日志分析脚本

```python
#!/usr/bin/env python3
"""日志分析脚本"""

import re
from datetime import datetime
from collections import defaultdict

def analyze_api_logs(log_file):
    """分析 API 日志"""
    api_stats = defaultdict(list)
    error_count = 0
    
    with open(log_file, 'r') as f:
        for line in f:
            # 解析 API 响应时间
            if "API Response:" in line:
                match = re.search(r'API Response: ([\w.]+) - ID: \d+ - Duration: ([\d.]+)s', line)
                if match:
                    method, duration = match.groups()
                    api_stats[method].append(float(duration))
            
            # 统计错误
            if "ERROR" in line:
                error_count += 1
    
    # 打印统计信息
    print("API 调用统计:")
    for method, durations in api_stats.items():
        avg_duration = sum(durations) / len(durations)
        print(f"  {method}: {len(durations)} 次调用, 平均响应时间: {avg_duration:.3f}s")
    
    print(f"\n总错误数: {error_count}")

if __name__ == "__main__":
    analyze_api_logs("logs/zabbix_api.log")
```

此手册提供了完整的远程主机测试指南，包括详细的配置说明、API 测试方法、日志监控和故障排除步骤。通过这些测试，您可以全面验证 Zabbix MCP 服务器的功能和性能。