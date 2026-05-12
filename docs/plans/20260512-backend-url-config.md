# 后端 URL 配置化 — 实施计划

## Context

当前 `http://127.0.0.1:8080` 硬编码在两处：
- `src-tauri/src/lib.rs:4` — Rust 端 21 个 Tauri command 使用
- `frontend/src/api/client.ts:19` — 前端路由表 + SSE 流 + brainstormStore 使用

问题：换端口要改两处源码；dev.sh 写的是 8000 跟代码里的 8080 不匹配；没有 Windows 启动脚本。

## 方案：环境变量 → Tauri managed state → 前端惰性获取

单一真相源：`SLOTH_BACKEND_URL` 环境变量（默认 `http://127.0.0.1:8080`）

```
SLOTH_BACKEND_URL (env var)
  ├── Rust: std::env::var → AppState.backend_url
  │     ├── 21 个 Tauri command 读 state.backend_url
  │     └── get_backend_url command 暴露给前端
  └── 前端: initBackendUrl() → invoke("get_backend_url") → 更新模块级 `let BACKEND`
        ├── client.ts 路由表 / SSE → 用 BACKEND（live binding）
        └── brainstormStore.ts → 用 BACKEND（live binding）
```

## 修改清单

### 1. `src-tauri/src/lib.rs` — Rust 侧

- **删** `const BACKEND_URL` + `fn http_client()`
- **增** `struct AppState { backend_url, http_client }`
- **增** `#[tauri::command] fn get_backend_url(state) -> String`
- **改** `run()` 加 `.setup()` 读取 `SLOTH_BACKEND_URL`，`.manage(AppState)`
- **改** 21 个 command handler：加 `state: tauri::State<'_, AppState>`，替换 `http_client()`/`BACKEND_URL`
- `greet` 不改

### 2. `frontend/src/api/client.ts`

- `export const BACKEND` → `export let BACKEND`（ES module live binding）
- 新增 `initBackendUrl()` 函数
- 其他函数无需改动

### 3. `frontend/src/main.tsx`

- async 初始化：先 `await initBackendUrl()`，再 `render(<App />)`

### 4. `dev.ps1` — 新增 Windows 启动脚本

### 5. `dev.sh` — 修复端口 + 设 env var

## 验证（全部通过 ✅）

1. ✅ `cargo build` — Rust 编译通过
2. ✅ `npm run test -- --run` — 49 测试全部通过
3. ✅ 启动完整应用 — 5 个 builtin agents / DeepSeek LLM / 15 个 inspirations 均正常
4. ✅ 设 `SLOTH_BACKEND_URL=http://127.0.0.1:9090` → 后端 9090 正常响应，Tauri 正确连接

## 实施总结

| 文件 | 改动 | 行数 |
|------|------|------|
| `src-tauri/src/lib.rs` | 删硬编码常量，加 AppState managed state，get_backend_url 命令，重构 21 个 command | +116/-100 |
| `frontend/src/api/client.ts` | `const`→`let` + `initBackendUrl()` | +16/-0 |
| `frontend/src/main.tsx` | async main() 包装 | +6/-2 |
| `dev.ps1` | 新增 Windows 启动脚本 | +56 |
| `dev.sh` | 端口 8000→8080 + SLOTH_BACKEND_URL | +5/-2 |
| `backend/app/database.py` | agent_templates.tools 列迁移 | +9/-0 |

**状态：✅ 已完成、已验证**
