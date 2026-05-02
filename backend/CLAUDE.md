# Backend CLAUDE (backend)

本文件定义后端实现与测试硬约束，适用于 `backend/app/` 下所有变更。

## 测试分层原则

1. 单元测试
   - 目标：验证业务逻辑正确性
   - 目录：`backend/tests/unit/`
   - 适用：`app/services/`、`app/models.py`、`app/database.py` 等

2. API 集成测试
   - 目标：验证路由契约与系统协作
   - 目录：`backend/tests/integration/`
   - 适用：`app/routers/` 及 API 对外行为

## 后端单元测试门禁

1. 触发条件
   - 修改或新增后端业务逻辑时，必须补对应单元测试

2. 最低 DoD
   - 至少 1 条核心成功路径
   - 至少 1 条关键边界或异常路径
   - 外部依赖（DB/网络/LLM）使用 mock，保持稳定和快速

3. 命令
   - `uv run --project backend python -m pytest backend/tests/unit -v`

## API 集成测试门禁

1. 触发条件
   - 修改或新增 API 路由时，必须补对应集成测试

2. 最低 DoD
   - 至少 1 条 2xx 成功路径
   - 至少 1 条 4xx/5xx 失败路径
   - 若路由具备鉴权或参数校验，必须覆盖

3. 命令
   - `uv run --project backend python -m pytest backend/tests/integration -v`

## 提交前检查（后端）

- 业务逻辑变更：跑 unit tests
- API 路由变更：跑 integration tests
- 必跑基线：
  - `uv run pytest tests/ -v`
  - 涉及评估时：`uv run pytest evals/ -v`

任一失败，不得合并。
