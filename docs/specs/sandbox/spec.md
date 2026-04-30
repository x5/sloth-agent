# 沙箱安全

> 归档参考: archive/initial-specs/20260416-17-sandbox-security-spec.md
> 最后更新: 2026-05-01
> 状态: 部分实现

## 概述

Agent 操作的隔离沙箱，防止对项目文件的无意修改。

## 已实现

- `backend/app/services/sandbox.py` — Brainstorm 会话沙箱
- 工具层风险门控（路径白名单 + 命令黑名单）

## 待实现

- 通用 sandbox 抽象层
- 网络隔离
- 资源限制（CPU / 内存 / 磁盘）
