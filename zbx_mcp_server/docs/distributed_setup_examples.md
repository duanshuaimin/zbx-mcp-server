# 分布式Zabbix服务器节点配置示例

## 概述

本文档提供了分布式Zabbix服务器节点管理的配置示例，展示如何在不同的部署场景中配置多个Zabbix服务器节点。

## 配置示例

### 1. 多数据中心部署

适用于跨地理位置的多数据中心监控环境：

```json
{
  "zabbix_servers": {
    "datacenter-beijing": {
      "name": "北京数据中心节点",
      "description": "负责监控北京数据中心的基础设施",
      "url": "https://zabbix-bj.company.com",
      "username": "admin",
      "password": "your_password",
      "timeout": 30,
      "verify_ssl": true
    },
    "datacenter-shanghai": {
      "name": "上海数据中心节点",
      "description": "负责监控上海数据中心的基础设施",
      "url": "https://zabbix-sh.company.com",
      "username": "admin",
      "password": "your_password",
      "timeout": 30,
      "verify_ssl": true
    },
    "datacenter-guangzhou": {
      "name": "广州数据中心节点",
      "description": "负责监控广州数据中心的基础设施",
      "url": "https://zabbix-gz.company.com",
      "username": "admin",
      "password": "your_password",
      "timeout": 30,
      "verify_ssl": true
    }
  },
  "default_zabbix_server": "datacenter-beijing"
}
```

### 2. 混合云部署

适用于本地数据中心和多个云平台的混合环境：

```json
{
  "zabbix_servers": {
    "onpremise-main": {
      "name": "本地主数据中心",
      "description": "企业内部主要数据中心的Zabbix服务器",
      "url": "https://zabbix.internal.company.com",
      "username": "admin",
      "password": "your_password",
      "timeout": 30,
      "verify_ssl": true
    },
    "aws-us-east": {
      "name": "AWS美东区域",
      "description": "AWS美东区域的Zabbix监控节点",
      "url": "https://zabbix-aws-east.company.com",
      "username": "admin",
      "password": "your_password",
      "timeout": 45,
      "verify_ssl": true
    },
    "azure-europe": {
      "name": "Azure欧洲区域",
      "description": "Azure欧洲区域的Zabbix监控节点",
      "url": "https://zabbix-azure-eu.company.com",
      "username": "admin",
      "password": "your_password",
      "timeout": 45,
      "verify_ssl": true
    },
    "gcp-asia": {
      "name": "GCP亚洲区域",
      "description": "Google Cloud亚洲区域的Zabbix监控节点",
      "url": "https://zabbix-gcp-asia.company.com",
      "username": "admin",
      "password": "your_password",
      "timeout": 45,
      "verify_ssl": true
    }
  },
  "default_zabbix_server": "onpremise-main"
}
```

### 3. 环境分离部署

适用于开发、测试、预发布、生产环境的完全分离：

```json
{
  "zabbix_servers": {
    "production": {
      "name": "生产环境",
      "description": "生产环境Zabbix监控系统",
      "url": "https://zabbix-prod.company.com",
      "username": "prod_admin",
      "password": "prod_password",
      "timeout": 30,
      "verify_ssl": true
    },
    "staging": {
      "name": "预发布环境",
      "description": "预发布环境Zabbix监控系统",
      "url": "https://zabbix-staging.company.com",
      "username": "staging_admin",
      "password": "staging_password",
      "timeout": 30,
      "verify_ssl": true
    },
    "testing": {
      "name": "测试环境",
      "description": "测试环境Zabbix监控系统",
      "url": "https://zabbix-test.company.com",
      "username": "test_admin",
      "password": "test_password",
      "timeout": 30,
      "verify_ssl": false
    },
    "development": {
      "name": "开发环境",
      "description": "开发环境Zabbix监控系统",
      "url": "http://zabbix-dev.internal:8080",
      "username": "dev_admin",
      "password": "dev_password",
      "timeout": 30,
      "verify_ssl": false
    }
  },
  "default_zabbix_server": "production"
}
```

### 4. 业务线分离部署

适用于大型企业按业务线分离的监控环境：

```json
{
  "zabbix_servers": {
    "ecommerce": {
      "name": "电商业务线",
      "description": "电商平台基础设施监控",
      "url": "https://zabbix-ecommerce.company.com",
      "username": "ecommerce_admin",
      "password": "your_password",
      "timeout": 30,
      "verify_ssl": true
    },
    "fintech": {
      "name": "金融科技业务线",
      "description": "金融科技平台监控",
      "url": "https://zabbix-fintech.company.com",
      "username": "fintech_admin",
      "password": "your_password",
      "timeout": 30,
      "verify_ssl": true
    },
    "gaming": {
      "name": "游戏业务线",
      "description": "游戏平台基础设施监控",
      "url": "https://zabbix-gaming.company.com",
      "username": "gaming_admin",
      "password": "your_password",
      "timeout": 30,
      "verify_ssl": true
    },
    "enterprise": {
      "name": "企业服务业务线",
      "description": "企业级服务平台监控",
      "url": "https://zabbix-enterprise.company.com",
      "username": "enterprise_admin",
      "password": "your_password",
      "timeout": 30,
      "verify_ssl": true
    }
  },
  "default_zabbix_server": "ecommerce"
}
```

## 分布式功能特性

### 1. 节点状态监控

```bash
# 获取所有节点的状态总览
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "zabbix_get_distributed_summary",
      "arguments": {}
    }
  }'
```

### 2. 聚合数据查询

```bash
# 从所有节点获取主机信息并聚合
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "zabbix_get_aggregated_hosts",
      "arguments": {}
    }
  }'
```

### 3. 分布式命令执行

```bash
# 在所有节点执行相同的API调用
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "zabbix_execute_on_all_nodes",
      "arguments": {
        "method": "hostgroup.get",
        "params": {
          "output": ["groupid", "name"]
        }
      }
    }
  }'
```

## 最佳实践

### 1. 网络连接配置

- 对于跨地域部署，适当增加timeout值（45-60秒）
- 内网环境可以禁用SSL验证以提高性能
- 公网环境务必启用SSL验证确保安全

### 2. 认证和安全

- 为不同环境使用不同的用户名和密码
- 生产环境建议使用强密码策略
- 考虑使用API Token代替用户名密码认证

### 3. 负载均衡

- 将default_zabbix_server设置为负载最轻的节点
- 根据地理位置选择最近的节点作为默认节点
- 考虑业务优先级设置默认节点

### 4. 监控和告警

- 使用distributed_summary定期检查所有节点状态
- 设置节点不可用时的故障转移策略
- 实现节点健康度监控和自动报警

### 5. 数据一致性

- 定期使用聚合功能检查数据一致性
- 实现配置同步机制确保各节点配置一致
- 建立数据备份和恢复策略