# Tool 调用子系统

> 归档参考: archive/initial-specs/20260416-02-tools-invocation-spec.md
> 最后更新: 2026-05-03
>
> **本文件描述 CLI Tool 系统（`src/sloth_agent/core/tools/`）。**
> Desktop Tool System（@desktop_tool 装饰器、function calling、Agent-Tool 绑定）见 `specs/tools/desktop-spec.md`。

## 概述

Agent 通过 Tool 层执行所有文件操作、Shell 命令和搜索。4 层调用链：ToolOrchestrator → ToolRegistry → RiskGate → HallucinationGuard。

## 已实现

### 4 层调用链 (`src/sloth_agent/core/tools/`)

```
ToolOrchestrator  →  ToolRegistry  →  RiskGate  →  HallucinationGuard  →  Formatter
   编排调度            注册/查找         风险门控        幻觉检测              输出格式化
```

- **ToolOrchestrator** — 接收 ToolCallRequest，调度完整调用链
- **ToolRegistry** — 管理所有可用 Tool 的注册与查找
- **RiskGate** — 路径白名单 + 命令黑名单检查
- **HallucinationGuard** — 检测 LLM 产生的文件/路径幻觉
- **Formatter** — 工具输出格式化

### 内置工具 (`src/sloth_agent/core/tools/builtin/`)

- `file_ops.py` — 文件读写（路径约束）
- `shell.py` — Shell 命令执行（命令黑名单）
- `search.py` — 代码搜索

### 配置

- `configs/tools.yaml` — Tool 定义与权限
- `configs/permissions.yaml` — 权限规则

## 待实现

- Plugin 扩展机制
- 自定义 Tool 的 YAML 声明式注册

## 关键接口

- `ToolOrchestrator.execute(state, call) → ToolResult`
- `ToolRegistry.register(name, tool)`
- `RiskGate.check(tool_name, params) → GateResult`
