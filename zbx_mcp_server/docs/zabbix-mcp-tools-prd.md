Zabbix MCP Server PRD 产品需求文档
====================================================

项目名称：Zabbix MCP Server
版本：v1.0
创建日期：2025年6月
文档类型：产品需求文档 (PRD)
开发框架：FastMCP 2.0

目录
====
1. 项目概述
2. 技术背景
3. 功能需求
4. 技术架构
5. 接口规范
6. 实施计划
7. 风险评估
8. 附录

1. 项目概述
===========

1.1 项目背景
-----------
随着企业IT基础设施的复杂化，多个Zabbix实例的统一管理和智能化运维成为迫切需求。传统的Zabbix管理方式存在以下痛点：
- 多实例管理分散，缺乏统一视图
- 监控数据分析依赖人工，效率低下
- 告警信息过载，根因分析困难
- 缺乏与AI助手的有效集成

1.2 项目目标
-----------
基于Model Context Protocol (MCP)规范，开发一个标准化的Zabbix MCP Server，实现：
- 统一管理多个Zabbix实例的日常运维操作
- 提供智能化的监控数据分析和报表生成
- 实现告警根因分析和智能建议
- 与各类AI助手（如Claude、ChatGPT等）无缝集成

1.3 目标用户
-----------
- 运维工程师：日常监控和故障处理
- 系统管理员：多实例管理和配置
- DevOps团队：自动化运维和CI/CD集成
- 技术主管：监控数据分析和决策支持

2. 技术背景
===========

2.1 MCP协议简介
--------------
Model Context Protocol (MCP)是由Anthropic推出的开放标准协议，用于标准化AI应用与外部数据源和工具的连接方式。MCP提供了一种类似"AI应用的USB-C"接口，使LLM能够安全、标准化地访问外部系统。

核心组件：
- MCP客户端：维护与服务器的1:1连接
- MCP服务器：轻量级程序，通过标准化协议暴露特定功能
- 本地数据源：文件、数据库、服务等
- 远程服务：通过API连接的外部系统

2.2 FastMCP框架
--------------
FastMCP是构建MCP服务器和客户端的Python框架，具有以下特点：
- Pythonic设计，简化开发流程
- 支持工具(Tools)、资源(Resources)、提示(Prompts)
- 内置部署、认证、代理等企业级功能
- 与官方MCP Python SDK兼容

2.3 Zabbix技术栈
---------------
- Zabbix API：REST API接口，支持JSON-RPC 2.0
- 数据库：MySQL/PostgreSQL存储监控数据
- 监控指标：主机、项目、触发器、事件等
- 告警机制：动作、媒体类型、用户群组

3. 功能需求
===========

3.1 核心功能模块
--------------

3.1.1 多实例管理模块
- 支持添加、删除、修改Zabbix实例配置
- 实例连接状态监控和自动重连
- 实例信息统一视图和健康状态检查
- 支持批量操作多个实例

3.1.2 监控数据管理模块
- 主机管理：查询、添加、修改、删除主机
- 监控项管理：创建、配置、启用/禁用监控项
- 触发器管理：配置告警规则和阈值
- 模板管理：导入、导出、应用监控模板
- 用户权限管理：用户组、权限分配

3.1.3 数据查询与分析模块
- 历史数据查询：支持时间范围、聚合函数
- 实时数据获取：最新监控值、状态信息
- 性能指标分析：CPU、内存、磁盘、网络等
- 自定义查询：支持复杂条件和多维度分析
- 数据导出：CSV、JSON、Excel格式

3.1.4 告警处理模块
- 告警事件查询：按时间、严重程度、状态筛选
- 告警统计分析：趋势分析、Top N分析
- 告警根因分析：关联分析、依赖关系梳理
- 告警处理：确认、关闭、批量操作
- 告警通知：邮件、短信、Webhook集成

3.1.5 报表生成模块
- 预定义报表：系统概览、性能趋势、可用性报告
- 自定义报表：灵活的报表配置和生成
- 报表调度：定时生成和自动发送
- 可视化图表：趋势图、饼图、柱状图等
- 报表分享：URL分享、PDF导出

3.1.6 运维自动化模块
- 批量配置：主机、监控项、触发器批量配置
- 自动发现：网络设备、服务自动发现和添加
- 配置同步：模板和配置在多实例间同步
- 维护窗口：自动设置和管理维护模式


3.2 MCP接口定义
--------------

3.2.1 工具(Tools)接口
- zabbix_get_hosts：获取主机列表
- zabbix_get_items：获取监控项数据
- zabbix_get_triggers：获取触发器信息
- zabbix_get_events：获取告警事件
- zabbix_get_problems：获取当前问题
- zabbix_create_host：创建新主机
- zabbix_update_host：更新主机配置
- zabbix_delete_host：删除主机
- zabbix_ack_event：确认告警事件
- zabbix_get_history：获取历史数据
- zabbix_execute_script：执行远程脚本
- zabbix_maintenance_create：创建维护窗口
- zabbix_export_template：导出模板
- zabbix_import_template：导入模板
- zabbix_generate_report：生成分析报告

3.2.2 资源(Resources)接口
- zabbix_instances：Zabbix实例配置信息
- monitoring_templates：监控模板库
- alert_rules：告警规则配置
- dashboard_configs：仪表板配置
- report_templates：报表模板



4. 技术架构
===========

4.1 整体架构
-----------
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │    │  Zabbix MCP     │    │   Zabbix API    │
│  (AI Assistant) │◄──►│     Server      │◄──►│   (Multiple)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Config Store  │
                       │   (JSON/SQLite) │
                       └─────────────────┘
```

4.2 核心组件
-----------

4.2.1 MCP服务器层
- FastMCP Server：MCP协议实现和消息路由
- 工具处理器：具体功能实现和业务逻辑
- 资源管理器：配置和模板资源管理
- 提示管理器：AI提示模板管理

4.2.2 业务逻辑层
- Zabbix API客户端：统一的API调用接口
- 数据处理引擎：数据清洗、转换、聚合
- 分析引擎：根因分析、趋势分析、异常检测
- 报表引擎：报表生成和渲染

4.2.3 数据存储层
- 配置存储：实例配置、用户设置
- 缓存存储：Redis缓存热点数据
- 临时存储：报表文件、导出数据

4.3 技术栈
---------
- 开发语言：Python 3.11+
- MCP框架：FastMCP 2.0
- HTTP客户端：httpx (异步)
- 数据处理：pandas, numpy
- 图表生成：matplotlib, plotly
- 配置管理：pydantic
- 日志记录：structlog
- 测试框架：pytest


5. 接口规范
===========

5.1 MCP工具接口示例
------------------

5.1.1 获取主机列表
```python
@mcp.tool
def zabbix_get_hosts(
    instance_name: str,
    group_name: Optional[str] = None,
    host_name: Optional[str] = None,
    status: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    获取指定Zabbix实例的主机列表
    
    Args:
        instance_name: Zabbix实例名称
        group_name: 主机组名称（可选）
        host_name: 主机名称模糊匹配（可选）
        status: 主机状态 0=启用 1=禁用（可选）
    
    Returns:
        主机信息列表，包含hostid, host, name, status等字段
    """
```

5.1.2 告警根因分析
```python
@mcp.tool
def zabbix_analyze_alert_root_cause(
    instance_name: str,
    event_id: str,
    time_range: int = 3600
) -> Dict[str, Any]:
    """
    分析告警的根本原因
    
    Args:
        instance_name: Zabbix实例名称
        event_id: 事件ID
        time_range: 分析时间范围（秒）
    
    Returns:
        根因分析结果，包含可能原因、相关事件、建议措施
    """
```

5.2 配置文件规范
--------------

5.2.1 实例配置
```json
{
    "instances": {
        "prod-zabbix": {
            "url": "https://zabbix.company.com",
            "username": "admin",
            "password": "encrypted_password",
            "timeout": 30,
            "verify_ssl": true,
            "max_retries": 3
        },
        "test-zabbix": {
            "url": "https://test-zabbix.company.com",
            "username": "admin",
            "password": "encrypted_password",
            "timeout": 30,
            "verify_ssl": false,
            "max_retries": 3
        }
    },
    "global_settings": {
        "cache_ttl": 300,
        "log_level": "INFO",
        "max_concurrent_requests": 10,
        "default_time_range": 3600
    }
}
```

