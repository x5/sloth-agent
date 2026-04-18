# 20260416-18-installation-onboarding-implementation-plan.md

> Spec 来源: `docs/specs/20260416-18-installation-onboarding-spec.md`（模块 18）
> Plan 文件: `docs/plans/20260416-18-installation-onboarding-implementation-plan.md`
> 对应 Arch: `docs/specs/00000000-00-architecture-overview.md` §9.0, §10
> v0.1.0 实现状态: 全局安装脚本 (install.sh / install.ps1) 已实现，采用 Claude Code 安装模型
> v0.1.0 实现文件: `scripts/install.sh`, `scripts/install.ps1`
> v0.2.0 规划: ConfigManager + config.json 统一配置 + `sloth config` CLI 命令

---

## 1. 目标

实现一键全局安装脚本，用户运行后可以在任何项目目录下使用 `sloth` 命令。
同时实现 `config.json` 统一配置管理机制，替代 `agent.yaml` 双文件模式。

---

## 2. 步骤

### 步骤 1: 实现 macOS/Linux 安装脚本

**文件**: `scripts/install.sh`（已实现 v0.1.0）

**内容** (spec §10):

采用 Claude Code 安装模型：

1. **自检**: 检查 git、uv、python3；uv 缺失自动下载安装
2. **克隆**: `git clone` 到 `~/.sloth-agent`（固定位置）
3. **安装**: 创建 `.venv`，`uv pip install -e .` 自动安装全部依赖
4. **CLI shim**: 创建 `~/.local/bin/sloth` 委托到 `.venv/bin/sloth`
5. **PATH**: 将 `~/.local/bin` 写入 shell profile
6. **验证**: 运行 `sloth --help` 确认
7. **Smoke test**: 运行 `evals.smoke_test` 验证流水线完整性
8. **API Key 模板**: 创建 `.env.example`，若环境变量有 Key 则自动填充 `.env`

**验收**: 新机器上 `curl ... | bash` 后可在任何目录运行 `sloth --help`

### 步骤 2: 实现 Windows PowerShell 安装脚本

**文件**: `scripts/install.ps1`（已实现 v0.1.0）

**内容** (spec §10):

与 install.sh 逻辑对齐：

1. **自检**: 检查 git、uv、python3；uv 缺失自动下载 `install.ps1` 安装
2. **克隆**: `git clone` 到 `%USERPROFILE%\.sloth-agent`
3. **安装**: 创建 `.venv`，`uv pip install -e .`
4. **CLI shim**: 创建 `%USERPROFILE%\.local\bin\sloth.ps1` + `sloth.bat`（cmd 兼容）
5. **PATH**: 将 `~/.local/bin` 写入 `$PROFILE`
6. **验证**: 运行 `sloth --help`
7. **Smoke test**: 运行 `evals.smoke_test`
8. **API Key 模板**: 创建 `.env.example`，自动填充

**验收**: 新机器上 `iwr ... | iex` 后可在任何目录运行 `sloth`

### 步骤 3: 实现 ConfigManager 核心模块

**文件**: `src/sloth_agent/core/config.py`（新建）

**内容** (spec §6.5):

```python
class ConfigManager:
    """加载和合并多层级 config.json，支持 user/project/local 三级。"""

    def load(self) -> SlothConfig:
        """按 local > project > user 深度合并后返回。"""

    def get_api_key(self, provider: str) -> str | None:
        """从 api_key_env 字段解析实际 API Key。"""
```

同时定义配置数据类：`SlothConfig`, `LLMConfig`, `ProviderConfig`, `AgentConfig`, `SecurityConfig`

**验收**: 三级配置文件正确合并，local 覆盖 user，project 覆盖 user

### 步骤 4: 创建 config.json 模板

**文件**: `configs/config.json.example`（新建）

包含完整的 LLM Provider、Agent、Execution、Chat、Security、Skills、Observability 配置段，`api_key_env` 引用环境变量名。

安装脚本在 Step 8 中同步创建此文件的全局副本。

**验收**: 模板文件可直接复制为 `~/.sloth-agent/config.json` 使用

### 步骤 5: 实现 `sloth config` CLI 命令

**文件**: `src/sloth_agent/cli/config_cmd.py`（新建）

```bash
sloth config                              # 查看合并后的完整配置
sloth config --scope user                 # 查看全局配置
sloth config set llm.default_provider qwen  # 修改当前层级
sloth config validate                     # 验证配置
sloth config env                          # 列出需要设置的 API Key
```

**验收**: 命令可正常显示、修改、验证配置

### 步骤 6: 编写测试

| 文件 | 覆盖 | 测试数 |
|------|------|--------|
| `tests/scripts/test_install_sh.py` | install.sh 语法检查 | 1 |
| `tests/core/test_config.py` | ConfigManager 三级合并 + API Key 解析 | 3 |
| `tests/cli/test_config_cmd.py` | `sloth config` CLI 命令调用 | 1 |

### 步骤 7: 交互式配置向导 `sloth config init --interactive`

**文件**: `src/sloth_agent/cli/config_init.py`（新建）

**内容** (spec §6.5.7):

交互流程：

1. **选择作用域**: user（全局 `~/.sloth-agent/`）/ project（当前目录 `.sloth/`）
2. **选择 Provider**: deepseek（推荐）/ qwen / kimi / glm / minimax / xiaomi
3. **输入 API Key**: 隐藏输入，写入 `.env`
4. **设置工作空间**: 默认 `./workspace`
5. **确认摘要**: 显示即将写入的文件和内容
6. **写入配置**: 创建/合并 config.json + .env
7. **验证**: `ConfigManager.validate()` + 显示结果

**技术要求：**
- 使用 `prompt_toolkit` 实现跨平台兼容输入
- API Key 使用 `prompt_toolkit.password` 隐藏输入
- 使用 Rich 表格展示确认摘要
- 支持 `Ctrl+C` 优雅退出
- 安装时自动添加 `prompt_toolkit>=3.0` 依赖

**验收：**
- 新用户可在 30 秒内完成首次配置
- API Key 输入时不显示明文
- 配置写入后可直接 `sloth config show` 查看
- Windows/macOS/Linux 三平台可用

### 步骤 8: 实现 `sloth uninstall` 卸载命令

**文件**: `src/sloth_agent/cli/uninstall_cmd.py`（已实现）

**内容** (spec §10.8):

1. **收集目标**: CLI shim (`~/.local/bin/sloth` + `.ps1` + `.bat`)、`~/.sloth-agent/` 目录
2. **PATH 清理**: 扫描 shell profile（`.zshrc`/`.bashrc`/`.profile`/`$PROFILE`），删除含 `# Sloth Agent` 注释的行及相邻空行
3. **Dry-run 模式**: `--dry-run` 列出将删除的内容，不实际删除
4. **Full 模式**: `--full` 额外删除 `config.json` 和 `.env`（默认保留配置）
5. **确认提示**: 交互式确认（`--yes` 跳过）
6. **执行删除**: 按顺序清理 shell profile → shim → 目录

**测试**: `tests/cli/test_uninstall_cmd.py`（9 tests）
- CollectItems: 目录存在/不存在、shim 包含
- CleanShellProfiles: 注释行删除、空列表无操作、无关内容保留
- DryRun: 不删除文件
- Actual: 删除 shim + 目录、负输入取消

**验收**:
- `sloth uninstall --dry-run` 显示列表但不删除
- `sloth uninstall` 交互式确认后清理
- `sloth uninstall --full` 完整清理（含配置）
- Shell profile 中 PATH 行被正确移除
- 所有测试通过（9 tests）

---

## 3. 文件清单

| 文件 | 动作 |
|------|------|
| `scripts/install.sh` | 已实现 (v0.1.0) + bugfix |
| `scripts/install.ps1` | 已实现 (v0.1.0) + bugfix |
| `src/sloth_agent/core/config_manager.py` | **新建** (v0.2.0) + bugfix |
| `configs/config.json.example` | **新建** (v0.2.0) |
| `src/sloth_agent/cli/config_cmd.py` | **新建** (v0.2.0) |
| `src/sloth_agent/cli/init_cmd.py` | **新建** (v0.2.0) |
| `tests/core/test_config_manager.py` | **新建** (v0.2.0) |
| `src/sloth_agent/cli/config_init.py` | **新建** |
| `tests/cli/test_config_init.py` | **新建** |
| `src/sloth_agent/cli/uninstall_cmd.py` | **新建** (v0.3.0) |
| `tests/cli/test_uninstall_cmd.py` | **新建** (v0.3.0) |

---

## 4. 验收标准

- [x] 安装脚本在干净环境可一键安装
- [x] CLI shim 可正常调用 `sloth --help`
- [x] config.json 模板可在安装后使用
- [x] `ConfigManager.load()` 正确合并三级配置
- [x] `ConfigManager.get_api_key()` 正确解析环境变量
- [x] `sloth config` 命令可正常显示/修改/验证
- [x] `sloth init` 命令可初始化项目目录
- [ ] 所有测试通过（共 14+ tests）
- [ ] `sloth config init --interactive` 可在 30 秒内完成首次配置
- [ ] API Key 输入时不显示明文
- [ ] Windows/macOS/Linux 三平台可用
- [x] `sloth uninstall` 命令可正常卸载
- [x] Shell profile 中 PATH 行被正确移除
- [x] 卸载命令所有测试通过（9 tests）

---

*Plan 版本: v1.1.0 | 创建: 2026-04-17*
