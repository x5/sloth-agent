# Phase 0 环境搭建问题记录 (2026-04-24)

## 1. Rust 编译缺少 C++ 编译器

**症状：** `cargo install create-tauri-app` 编译失败，提示缺少 C/C++ compiler。
**原因：** Windows 上 Rust 需要 MSVC 工具链。
**解决：** 安装 Visual Studio Build Tools 2022，勾选「使用 C++ 的桌面开发」工作负载。

## 2. tauri-build 缺少 build.rs

**症状：** `tauri::generate_context!()` 报错 `OUT_DIR env var is not set`。
**原因：** Tauri v2 需要 `build.rs` 来触发构建脚本，生成 OUT_DIR。
**解决：** 在 `src-tauri/build.rs` 中添加：
```rust
fn main() { tauri_build::build() }
```
并在 `Cargo.toml` 中添加 `[build-dependencies]` → `tauri-build`。

## 3. Windows 图标文件缺失

**症状：** `tauri-build` 报错 `icons/icon.ico not found; required for generating a Windows Resource file`。
**解决：** 在 `src-tauri/icons/` 下放置有效的 `.ico` 文件（至少包含 16x16 32bit）。

## 4. 包名与模块名不一致

**症状：** `sloth_agent_lib::run()` 编译报错 `use of unresolved module`。
**原因：** Cargo 包名中的连字符 `-` 会被转换为下划线 `_`。包名 `sloth-agent` → 模块名 `sloth_agent`。
**解决：** 使用 `sloth_agent::run()`。

## 5. 端口被占用 (1420 / 8000)

**症状：** Vite 报 `Port 1420 is already in use`；FastAPI 报 `WinError 10013`。
**原因：** 之前的 Vite/uvicorn 进程未正常退出，端口残留。端口 8000 还可能被 Windows Hyper-V 保留。
**解决：**
- `netstat -ano | grep <port>` 找 PID
- `taskkill //PID <PID> //F`
- 如果端口被 Hyper-V 保留（如 8000），换其他端口（如 8080）

## 6. WebView 中 `fetch` 无法请求外部 HTTP 地址

**症状：** 前端 `fetch('http://localhost:8000/...')` 报 `Failed to fetch`。
**原因：** Tauri v2 的 WebView 安全策略不允许浏览器原生 `fetch` 请求到外部地址。
**解决：** 不要用浏览器 `fetch`，改用 Tauri 的 `invoke` 调用 Rust 命令，由 Rust 端发 HTTP 请求。

## 7. Tauri HTTP 插件 scope 配置格式

**症状：** `url not allowed on the configured scope: http://localhost:8000/api/echo`。
**原因：** Tauri v2 HTTP 插件的 URL scope 需要内联在 capability 的 `permissions` 数组中，不能放在 `plugins.http` 配置块或根 `scope` 字段。
**正确格式（capabilities/default.json）：**
```json
{
  "permissions": [
    {
      "identifier": "http:default",
      "allow": [
        { "url": "http://localhost:*" },
        { "url": "http://127.0.0.1:*" }
      ]
    }
  ]
}
```
**最终方案：** 放弃 HTTP 插件，改用 Rust `reqwest` 直接代理。

## 8. Tauri HTTP 插件 `fetch` 解析响应体失败

**症状：** `Failed to execute 'close' on 'ReadableStreamDefaultController': Unexpected end of JSON input`。
**原因：** Tauri HTTP 插件的 `fetch` API 和浏览器 `fetch` 在处理响应体流时有差异。
**解决：** 放弃 HTTP 插件，改用 `invoke` → Rust `reqwest` 方案。

## 9. reqwest 遇到系统代理返回 503

**症状：** Rust 端 `reqwest` 请求 `http://localhost:8080` 返回 `503 Service Unavailable`，但 `curl` 直接请求后端返回 200 OK，后端日志也显示 200。
**原因：** reqwest 默认读取系统代理设置（Windows 代理/防火墙/安全软件），将 localhost 请求路由到了代理服务器，代理返回 503。
**解决：**
1. 使用 `.no_proxy()` 禁用系统代理：`reqwest::Client::builder().no_proxy().build()`
2. 使用 `127.0.0.1` 代替 `localhost`（绕过 DNS 解析可能触发的代理规则）

## 10. FastAPI CORS 预检失败 (OPTIONS 405)

**症状：** 前端浏览器请求报 CORS 错误，后端日志显示 `OPTIONS /api/echo HTTP/1.1" 405 Method Not Allowed`。
**原因：** FastAPI CORSMiddleware 默认不会处理 OPTIONS 预检的 405 响应。
**解决：** 虽然最终改用 Rust 代理方案绕过了这个问题，但如果未来需要直接前端→后端通信，需要确保 CORS 配置正确：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或具体 origin
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 架构总结

最终采用的通信架构：
```
Tauri WebView (React)  ──invoke──>  Rust Layer (reqwest, no_proxy)
                                                    │
                                                    ▼
                                        FastAPI Sidecar (127.0.0.1:8080)
```

关键决策：
- 前端不直接发 HTTP 请求，统一通过 `invoke` 调用 Rust 命令
- Rust 层作为代理，用 `reqwest` 与 FastAPI 通信
- 使用 `127.0.0.1` 而非 `localhost`，加 `.no_proxy()` 避免系统代理干扰
