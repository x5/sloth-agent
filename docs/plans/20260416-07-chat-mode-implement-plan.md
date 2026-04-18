# 20260416-07-chat-mode-implement-plan.md

> Spec 来源: `docs/specs/20260416-07-chat-mode-spec.md`
> Plan 文件: `docs/plans/20260416-07-chat-mode-implement-plan.md`
> 对应 Arch: `docs/specs/00000000-00-architecture-overview.md` §5, §7.2
> v1.0 状态: 已实现 (v0.2 release)
> v1.1 状态: 已实现 (v0.2 release)
> v1.2 状态: 未实现，远期规划
> v1.3 状态: 本计划重点

---

## 1. 目标

完善 Chat Mode 的 CLI 用户体验，使非技术用户（产品经理、项目管理人员）能够有效使用 `sloth chat`。同时补齐 v1.1 已标记但实际未完全落地的部分。

---

## 2. 步骤

### 步骤 1: v1.0 基础回顾（已实现，不需编码）

v1.0 已实现的能力：
- `sloth chat` 命令进入 REPL 交互循环
- 基础 slash commands: `/clear`, `/context`, `/help`, `/quit`, `/skills`, `/scenarios`, `/tools`
- 消息历史截断管理（保留最近 20 条）
- 复用 LLMProviderManager

**已知问题**: 消息只在内存中，退出后丢失（由 Chat-1 消息持久化修复任务处理）

### 步骤 2: v1.1 回顾与修复

v1.1 已实现但需要完善的部分：

| 能力 | 当前状态 | 需要做什么 |
|------|----------|-----------|
| `/skill <name>` | 只打印 markdown 内容 | 接 SkillRegistry 实际执行 |
| `/start autonomous` | Controller 存在，executor 是 placeholder | 接真实 Runner 流水线 |
| `/stop` | 已实现 | 无需改动 |
| `/status` | 已实现 | 无需改动 |

**注意**: `/skill` 实际执行和 Autonomous 接真实流水线属于 Chat-2 和 Chat-3 任务，依赖 Phase Pipeline 和 Skill Management，不在此计划范围内。

### 步骤 3: 实现 `src/sloth_agent/cli/chat_ux.py`

核心 UX 模块，封装所有 v1.3 友好化功能：

```python
"""CLI User Experience helpers — welcome screen, natural help, confirm cards, progress."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table


class ChatUX:
    """CLI user experience helpers for non-technical users."""

    def __init__(self, console: Console):
        self.console = console

    def show_welcome(self, workspace: Path, model_info: str, skill_count: int,
                     suggested_questions: list[str] | None = None) -> None:
        """显示欢迎信息。

        Args:
            workspace: 当前工作目录
            model_info: 当前模型信息字符串
            skill_count: 已加载技能数
            suggested_questions: 预设问题列表（None 时根据 workspace 自动生成）
        """

    def generate_suggested_questions(self, workspace: Path) -> list[str]:
        """根据工作目录内容动态生成预设问题。

        检测规则:
        - 有 plan .md 文件 → "执行 plan 文件中的开发计划"
        - 有 .py/.ts/.js 代码文件 → "审查当前代码质量"
        - 有 test_ 文件 → "运行测试并分析报告"
        - 有 TODO.md → "查看当前任务清单"
        - git 有未提交更改 → "查看当前的代码变更"
        - 默认 → "帮我写一个需求文档"
        """

    def show_natural_help(self, common_commands: dict[str, str],
                          advanced_commands: dict[str, str],
                          session_id: str, skill_count: int) -> None:
        """显示自然语言帮助。

        结构:
        1. 能力描述 Panel（emoji + 动词短语）
        2. 常用命令 Table（仅 5 个）
        3. 折叠的高级命令列表
        4. 当前会话状态行
        """

    def show_structured_result(self, title: str, rows: list[tuple],
                               headers: list[str]) -> None:
        """用 Rich table 呈现结构化信息。"""

    def show_diff_preview(self, filepath: str, diff_lines: list[str]) -> None:
        """显示文件修改预览（diff 样式，绿色=新增，红色=删除）。"""

    def show_confirm(self, file_changes: list[dict],
                     commands: list[str]) -> bool:
        """显示确认卡片，返回用户选择。

        Args:
            file_changes: [{"file": "path", "lines": 17, "type": "modify|new"}]
            commands: 即将运行的命令列表

        Returns:
            True = 用户确认执行，False = 取消
        """

    def show_delete_confirm(self, filepath: str, content_preview: str) -> bool:
        """删除文件二次确认，需输入 DELETE 确认。"""

    def create_progress(self, steps: list[str]) -> Progress:
        """创建多步骤进度指示器。"""

    def show_status_panel(self, phase: str, progress_pct: int,
                          completed: list[str], current: str,
                          pending: list[str], elapsed: str) -> None:
        """显示自主模式状态面板。"""

    def show_error(self, message: str, retry_count: int = 0) -> None:
        """显示错误状态指示。"""
```

**验收**: 模块可导入，各方法无语法错误，类型检查通过

### 步骤 4: 欢迎屏集成

**集成点**: `EnhancedChatSession.loop()` 入口

**改动**:
1. 在 REPL 循环开始前调用 `ChatUX.show_welcome()`
2. 传入 workspace 路径、当前模型信息、已加载技能数
3. 预设问题通过 `generate_suggested_questions()` 动态生成
4. 用户输入数字时自动映射为对应问题文本

**预设问题生成逻辑**:

```python
def generate_suggested_questions(workspace: Path) -> list[str]:
    questions = ["帮我写一个需求文档"]  # 默认

    # 检测 plan 文件
    for name in ["plan.md", "PLAN.md", "plan.md", "开发计划.md"]:
        if (workspace / name).exists():
            questions.append(f"执行 {name} 中的开发计划")
            break

    # 检测代码文件
    code_exts = {".py", ".ts", ".js", ".go", ".rs"}
    if any(f.suffix in code_exts for f in workspace.iterdir() if f.is_file()):
        questions.append("审查当前代码质量")

    # 检测测试文件
    if any(f.name.startswith("test_") for f in workspace.iterdir() if f.is_file()):
        questions.append("运行测试并分析报告")

    # 检测 TODO
    if (workspace / "TODO.md").exists():
        questions.append("查看当前任务清单")

    # 检测 git 变更 (subprocess git status)
    ...

    return questions[:4]  # 最多 4 个
```

**验收**: 启动 chat 时显示品牌欢迎屏，预设问题根据目录内容动态变化

### 步骤 5: 自然语言帮助

**集成点**: `EnhancedChatSession._handle_slash("/help")`

**改动**: 替换现有的简单命令列表输出，改为 `ChatUX.show_natural_help()`

**内容规范**:
- 能力描述区块: 5 个核心能力，emoji + 动词短语 + 白话说明
- 常用命令: `/help`, `/clear`, `/status`, `/skills`, `/quit`
- 高级命令: 折叠在 "── 高级命令 ──" 分隔线下方
- 状态行: session ID + 已加载技能数

**验收**: `/help` 输出非技术用户可读的帮助信息

### 步骤 6: 中文优先

**改动**:
1. REPL 的 system prompt 改为中文: `"你是 Sloth Agent，一个 AI 开发助手。"`
2. 所有硬编码的英文提示文本改为中文:
   - `"Conversation cleared"` → `"对话已清空"`
   - `"Goodbye!"` → `"再见！"`
   - `"Tool error"` → `"工具执行错误"`
   - 等
3. 错误信息统一格式: `"[red]错误: {中文描述}[/red]"`
4. 确认提示: `"确认执行？[Y/n]: "`
5. 保留英文兼容: 用户输入英文时 LLM 自动英文回复（系统提示已包含语言跟随指令）

**验收**: 所有 REPL 输出（欢迎屏、帮助、错误、确认、进度）均为中文

### 步骤 7: 结构化输出

**集成点**: REPL 的多个输出位置

| 位置 | 改动 |
|------|------|
| `_list_tools()` | 输出改为 `ChatUX.show_structured_result` 的 Table: [工具名, 用途, 风险等级] |
| `_list_skills()` | 输出改为 Table: [技能名, 用途, 版本] |
| Reviewer 结果 | Table: [文件名, 问题描述, 严重程度]，严重程度用颜色编码 |
| `_handle_slash("/context")` | 输出改为 Key-Value Table: [配置项, 当前值] |
| 文件变更 | `ChatUX.show_diff_preview()` 渲染 diff |

**验收**: 上述场景输出为格式化的 Rich 组件，非大段纯文本

### 步骤 8: 确认卡片

**集成点**: `_handle_tool_calls()` 中的高风险工具确认

**改动**: 替换现有的 `input("Execute? (y/N) ")` 为 `ChatUX.show_confirm()`

**确认规则实现**:

| 操作 | 行为 |
|------|------|
| 写文件 | 显示文件名 + 变更行数，默认 Y |
| 多文件写 | 合并为一张卡片显示，默认 Y |
| 运行命令 | 显示完整命令字符串，默认 Y |
| 删除文件 | 二次确认，需输入 "DELETE" |
| 已知安全命令 (pytest, lint) | 跳过确认 |

**审批疲劳缓解**:
- 合并同类操作
- 显示变更摘要而非全文
- 安全命令跳过确认

**验收**: 高风险操作前显示确认卡片，默认 Y，删除需二次确认

### 步骤 9: 进度可视化

**集成点**: REPL 的多处

| 位置 | 改动 |
|------|------|
| LLM 请求期间 | `ChatUX.create_progress()` 创建 spinner "正在思考…" |
| 工具执行期间 | spinner 显示 "正在执行 {工具名}…" |
| 自主模式多步骤任务 | 多步骤 Progress bar + 步骤列表 |
| `/status` 命令 | `ChatUX.show_status_panel()` 渲染状态面板 |
| 错误状态 | `ChatUX.show_error()` 显示错误指示 |
| 长时间无输出 | 每 10s 追加 "仍在处理中…" 提示 |

**验收**: LLM 请求和工具执行期间有可视化进度指示，自主模式有状态面板

---

## 3. REPL 集成点汇总

修改 `src/sloth_agent/chat/repl.py` 的以下位置：

| 行/方法 | 改动内容 |
|---------|----------|
| `loop()` 入口 | 调用 `ChatUX.show_welcome()` |
| `_handle_slash("/help")` | 调用 `ChatUX.show_natural_help()` |
| `_process_message()` | 进度 spinner 包装 LLM 请求 |
| `_handle_tool_calls()` | 确认提示改为 `ChatUX.show_confirm()` |
| `_list_tools()` | 输出改为 Rich table |
| `_list_skills()` | 输出改为 Rich table |
| `_handle_slash("/context")` | 输出改为 Key-Value table |
| `_show_status()` | 调用 `ChatUX.show_status_panel()` |
| 全局 | 硬编码英文提示替换为中文 |

---

## 4. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/cli/chat_ux.py` | **新建** |
| `src/sloth_agent/chat/repl.py` | **修改**（9 个集成点） |
| `tests/cli/test_chat_ux.py` | **新建**（9+ tests） |

---

## 5. 测试策略

| 测试文件 | 测试数 | 覆盖内容 |
|----------|--------|----------|
| `test_welcome_screen_shown` | 1 | 启动时显示欢迎信息，输出包含 "欢迎" 和预设问题 |
| `test_welcome_context_aware` | 1 | 有 plan 文件时生成 "执行 plan" 建议，有代码时生成 "审查代码" 建议 |
| `test_welcome_default_questions` | 1 | 无特殊文件时使用默认问题 |
| `test_natural_help_format` | 1 | /help 输出包含能力描述区块，非纯命令列表 |
| `test_natural_help_advanced_folded` | 1 | 高级命令折叠在分隔线下方 |
| `test_chinese_system_prompt` | 1 | REPL system prompt 包含中文字符 |
| `test_chinese_error_messages` | 1 | 错误信息为中文格式 |
| `test_structured_output_table` | 1 | 工具列表输出为 Rich Table 格式 |
| `test_confirm_card_shown` | 1 | 高风险操作显示确认卡片，包含文件列表 |
| `test_confirm_card_default_yes` | 1 | 空输入视为确认（默认 Y） |
| `test_delete_confirm_requires_explicit` | 1 | 删除文件需要输入 DELETE 确认 |
| `test_safe_command_skip_confirm` | 1 | pytest/lint 等安全命令跳过确认 |
| `test_progress_spinner` | 1 | LLM 请求期间显示 spinner |
| `test_progress_bar_multistep` | 1 | 多步骤任务显示进度条 + 步骤列表 |
| `test_status_panel` | 1 | /status 输出为格式化状态面板 |
| `test_diff_preview` | 1 | diff 预览使用颜色编码（绿=新增，红=删除） |

---

## 6. 验收标准

- [ ] `sloth chat` 启动显示品牌欢迎屏 + 动态预设问题
- [ ] `/help` 显示自然语言帮助，包含能力描述，非技术用户可读
- [ ] 系统提示默认使用中文，错误信息为中文
- [ ] 结构化信息（审查结果、工具列表等）使用 Rich table
- [ ] 高风险操作前显示确认卡片，默认 Y
- [ ] 删除文件需二次确认（输入 DELETE）
- [ ] 安全命令（pytest/lint）跳过确认
- [ ] LLM 请求和工具执行期间有可视化进度指示
- [ ] 自主模式有格式化状态面板
- [ ] 所有测试通过（16+ tests）
- [ ] 不引入新依赖（仅使用已有的 rich）

---

*Plan 版本: v1.0.0 | 创建: 2026-04-18*
