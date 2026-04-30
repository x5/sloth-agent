# 安装与初始化

> 归档参考: archive/initial-specs/20260416-18-installation-onboarding-spec.md
> 最后更新: 2026-05-01
> 状态: 部分实现

## 概述

CLI 安装脚本、项目初始化向导。

## 已实现

- `cli/init_cmd.py` — 项目初始化命令
- `cli/uninstall_cmd.py` — 卸载命令
- `scripts/install.sh`, `scripts/install.ps1` — 安装脚本

## 待实现

- 交互式安装向导
- 依赖自动检测
- 平台兼容性矩阵
