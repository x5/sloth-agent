# 守护进程与健康检查

> 归档参考: archive/initial-specs/20260416-16-daemon-health-spec.md
> 最后更新: 2026-05-01
> 状态: 部分实现
> Scope: Desktop

## 概述

后台守护进程、健康检查、看门狗。

## 已实现

- `reliability/watchdog.py` — 基础看门狗

## 待实现

- 守护进程模式
- 健康检查 HTTP 端点
- 自动重启
