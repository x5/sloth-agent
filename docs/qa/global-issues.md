# Issue Log

Tracked bugs, UX issues, and discoveries from hands-on review or user feedback.

---

## Open

### #6 安装脚本输出 4 步 Next Steps 但实际有额外要求
**Severity:** P2
**Discovered:** 2026-04-18, end-to-end install flow review
**Description:** 安装脚本末尾告诉用户 4 步完成，但实际上用户还需要执行 `sloth config init --interactive` 或手动编辑 `.env`。如果用户只跑安装脚本，所有命令都会因缺 Key 而失败。
**Fix idea:** 安装脚本结束后提示运行 `sloth config init -i` 作为第一步。

---

## Resolved

### #1 `sloth init` command missing
**Severity:** P0 | **Fixed:** 2026-04-18
**Description:** Install script told users to run `sloth init` but no such command existed.
**Fix:** Created `src/sloth_agent/cli/init_cmd.py` with `init` command that creates `.sloth/config.json`, `.env`/`.env.example`, and `local_skills/` directory. Registered in `app.py`.
**Files:** `init_cmd.py` (new), `app.py` (modified)

### #2 `.env` not loaded by ConfigManager
**Severity:** P0 | **Fixed:** 2026-04-18
**Description:** `config_manager.py` read `os.environ` directly without calling `load_dotenv()`, so `.env` files were never loaded.
**Fix:** Added `_ensure_env_loaded()` method that loads project `.env` first (override=True), then global `.env` (override=False). Calls `load_dotenv()` lazily on first `load()` call.
**Files:** `config_manager.py` (modified), `test_config_manager.py` (added 3 env loading tests)

### #3 `install.sh` config.json copy path fails in curl|bash mode
**Severity:** P1 | **Fixed:** 2026-04-18
**Description:** `$(dirname "$0")/../configs/config.json.example` fails when piped via `curl | bash` ($0=/dev/stdin).
**Fix:** Changed to `$SLOTH_DIR/configs/config.json.example` (absolute path from cloned repo). Same fix in `install.ps1`.
**Files:** `install.sh`, `install.ps1` (modified)

### #4 `.env.example` mismatch with config.json providers
**Severity:** P1 | **Fixed:** 2026-04-18
**Description:** 6 providers in config.json but only 2 uncommented keys in `.env.example`, causing `sloth config env` to list 6 missing keys.
**Fix:** Added `is_optional` field to `ProviderConfig` dataclass. Marked kimi/glm/minimax/xiaomi as optional in `config.json.example`. `get_required_env_vars()` now skips optional providers. Updated both `.env.example` templates to comment out optional keys.
**Files:** `config_manager.py`, `config.json.example`, `install.sh`, `install.ps1` (all modified)

### #5 Windows unicode character encoding issue
**Severity:** P2 | **Fixed:** 2026-04-18
**Description:** `init_cmd.py` used unicode checkmark (`\u2713`) which fails on Windows consoles with GBK encoding.
**Fix:** Replaced with ASCII-safe `[+]` marker.
**Files:** `init_cmd.py` (modified)
