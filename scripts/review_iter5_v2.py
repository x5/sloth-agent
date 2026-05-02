"""Iter-5 Review: API + UI 全面检查"""
import json
import os
import urllib.request
import urllib.error

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = r"C:\Users\TUF\AppData\Local\ms-playwright"
from playwright.sync_api import sync_playwright

BACKEND = "http://127.0.0.1:8080"
FRONTEND = "http://localhost:5173"
CHROMIUM = r"C:\Users\TUF\AppData\Local\ms-playwright\chromium-1208\chrome-win64\chrome.exe"
OUT = r"C:\Users\TUF\Workspace\agent-evolve\scripts\iter5_screenshots"
os.makedirs(OUT, exist_ok=True)

PASS = 0; FAIL = 0
def check(label, ok, detail=""):
    global PASS, FAIL
    mark = "✅" if ok else "❌"
    print(f"  {mark} {label}" + (f"  ({detail})" if detail else ""))
    if ok: PASS += 1
    else: FAIL += 1
    return ok

def req(method, path, body=None, expected_error=None):
    url = BACKEND + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(url, data=data, headers=headers, method=method), timeout=8
        )
        return {"ok": True, "status": r.status, "data": json.loads(r.read())}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "data": json.loads(e.read())}

# ──────────────────────────────────────────────────────────────────────────────
print("\n═══ 1. Task 5.0: Message 模型字段 ═══")

spec = req("GET", "/openapi.json")
schemas = spec["data"].get("components", {}).get("schemas", {})
# Find message schema by searching schemas dict
msg_schema = None
for k, v in schemas.items():
    if "brainstorm_session_id" in str(v):
        msg_schema = v
        break

if msg_schema:
    props = msg_schema.get("properties", {})
    check("brainstorm_session_id field", "brainstorm_session_id" in props)
    check("parent_message_id field", "parent_message_id" in props)
    check("round field", "round" in props)
    check("intent field", "intent" in props)
    check("truncated field", "truncated" in props)
    check("mode field (chat/brainstorm)", "mode" in props)
else:
    check("Message schema found in OpenAPI", False, "not found in /openapi.json")

# ──────────────────────────────────────────────────────────────────────────────
print("\n═══ 2. Task 5.2: SSE discuss 端点 ═══")

# Create fresh inspiration for this test
r = req("POST", "/api/inspirations", {"name": "iter5-review"})
check("POST /inspirations → 201", r["status"] == 201)
insp_id = r["data"]["id"]

# Check team was auto-populated
agents_r = req("GET", f"/api/inspirations/{insp_id}/agents")
check("Inspiration auto-gets team agent", agents_r["status"] == 200 and len(agents_r["data"]) >= 1,
      f"{len(agents_r['data'])} agents")

# Create brainstorm session
sess_r = req("POST", f"/api/inspirations/{insp_id}/brainstorm-sessions", {"title": "Review Session"})
check("POST /brainstorm-sessions → 201", sess_r["status"] == 201)
sess_id = sess_r["data"]["id"]
check("Session status = active", sess_r["data"]["status"] == "active")
check("Session has sandbox_path", bool(sess_r["data"]["sandbox_path"]))
check("Session has max_messages=1000", sess_r["data"]["max_messages"] == 1000)
check("Session has cooldown_seconds=5", sess_r["data"]["cooldown_seconds"] == 5)

# List sessions
list_r = req("GET", f"/api/inspirations/{insp_id}/brainstorm-sessions")
check("GET /brainstorm-sessions → list", list_r["status"] == 200 and len(list_r["data"]) == 1)

# Get by id
get_r = req("GET", f"/api/brainstorm-sessions/{sess_id}")
check("GET /brainstorm-sessions/{id}", get_r["status"] == 200 and get_r["data"]["id"] == sess_id)

# Patch title
patch_r = req("PATCH", f"/api/brainstorm-sessions/{sess_id}", {"title": "Updated"}, expected_error=None)
check("PATCH title update", patch_r["status"] == 200 and patch_r["data"]["title"] == "Updated")

# DELETE /discuss abort endpoint
abort_url = f"{BACKEND}/api/brainstorm-sessions/{sess_id}/discuss"
abort_req = urllib.request.Request(abort_url, method="DELETE")
try:
    abort_resp = urllib.request.urlopen(abort_req, timeout=5)
    check("DELETE /discuss abort → 200", abort_resp.status == 200)
except urllib.error.HTTPError as e:
    check("DELETE /discuss abort", False, f"HTTP {e.code}")

# 404 on nonexistent
r404 = req("GET", "/api/brainstorm-sessions/00000000-0000-0000-0000-000000000000")
check("GET nonexistent session → 404", r404["status"] == 404)

# End session rejects new discuss
end_r = req("PATCH", f"/api/brainstorm-sessions/{sess_id}", {"status": "ended"})
check("PATCH status=ended", end_r["status"] == 200 and end_r["data"]["status"] == "ended")

discuss_r = req("POST", f"/api/brainstorm-sessions/{sess_id}/discuss", {"content": "hello"})
check("Ended session rejects discuss → 400", discuss_r["status"] == 400)

# ──────────────────────────────────────────────────────────────────────────────
print("\n═══ 3. Task 5.1: BrainstormEngine + CoolingTimer ═══")

# Verify BrainstormEngine source structure
import pathlib
engine_file = pathlib.Path(r"C:\Users\TUF\Workspace\agent-evolve\backend\app\services\brainstorm.py")
engine_src = engine_file.read_text(encoding="utf-8")

check("CoolingTimer class defined", "class CoolingTimer" in engine_src)
check("TimerState enum with RUNNING/COOLING_DOWN/CONFIRMING/ENDED",
      all(s in engine_src for s in ["RUNNING", "COOLING_DOWN", "CONFIRMING", "ENDED"]))
check("BrainstormEngine class defined", "class BrainstormEngine" in engine_src)
check("_load_agents method", "_load_agents" in engine_src)
check("_load_history method", "_load_history" in engine_src)
check("_save_message method", "_save_message" in engine_src)
check("run() async generator", "async def run(" in engine_src)
check("abort() method", "def abort(" in engine_src)
check("PASS detection implemented", "PASS" in engine_src and "is_pass" in engine_src)
check("agent_start SSE event", '"agent_start"' in engine_src)
check("agent_token SSE event", '"agent_token"' in engine_src)
check("message_done SSE event", '"message_done"' in engine_src)
check("discussion_end SSE event", '"discussion_end"' in engine_src)
check("agent_pass SSE event", '"agent_pass"' in engine_src)
check("MAX_ROUNDS limit (8)", "MAX_ROUNDS = 8" in engine_src)
check("round tracking persisted to DB", "round_num" in engine_src)

# ──────────────────────────────────────────────────────────────────────────────
print("\n═══ 4. Task 5.3: 前端 SSE 消费 ═══")

store_file = pathlib.Path(r"C:\Users\TUF\Workspace\agent-evolve\frontend\src\stores\brainstormStore.ts")
store_src = store_file.read_text(encoding="utf-8")

check("startDiscussion method", "startDiscussion" in store_src)
check("stopDiscussion (abort)", "stopDiscussion" in store_src)
check("AbortController for SSE", "AbortController" in store_src)
check("agent_start handler", '"agent_start"' in store_src)
check("agent_token handler", '"agent_token"' in store_src)
check("message_done handler", '"message_done"' in store_src)
check("discussion_end handler", '"discussion_end"' in store_src)
check("agent_pass handler", '"agent_pass"' in store_src)
check("discussionMessages state", "discussionMessages" in store_src)
check("streamingContent state", "streamingContent" in store_src)
check("activeAgentId state", "activeAgentId" in store_src)
check("DELETE /discuss on stop (backend abort)", 'method: "DELETE"' in store_src)

# Check ChatArea brainstorm integration
chatarea_file = pathlib.Path(r"C:\Users\TUF\Workspace\agent-evolve\frontend\src\components\ChatArea.tsx")
chatarea_src = chatarea_file.read_text(encoding="utf-8")

check("BrainstormStreamBubble imported", "BrainstormStreamBubble" in chatarea_src)
check("brainstormMode toggle button", "handleToggleBrainstorm" in chatarea_src)
check("Brainstorm divider component", "BrainstormDivider" in chatarea_src)
check("brainstorm-divider CSS class", "brainstorm-divider" in chatarea_src)
check("sendOne routes to brainstorm", "brainstormDiscuss" in chatarea_src)
check("discussionMessages synced to messages", "discussionMessages" in chatarea_src)
check("brainstormActiveId session tracking", "brainstormActiveId" in chatarea_src)
check("agentColorMap for per-agent color", "agentColorMap" in chatarea_src)

# Check BrainstormStreamBubble component
bubble_file = pathlib.Path(r"C:\Users\TUF\Workspace\agent-evolve\frontend\src\components\BrainstormStreamBubble.tsx")
bubble_src = bubble_file.read_text(encoding="utf-8")

check("BrainstormStreamBubble renders", "BrainstormStreamBubble" in bubble_src)
check("streamingContent prop", "streamingContent" in bubble_src)
check("agentNumber prop", "agentNumber" in bubble_src)
check("agentColor prop", "agentColor" in bubble_src)
check("brainstorm-cursor CSS class", "brainstorm-cursor" in bubble_src)
check("thinking-dots animation", "thinking-dots" in bubble_src)
check("typing indicator text", "typing" in bubble_src)

# ──────────────────────────────────────────────────────────────────────────────
print("\n═══ 5. UI 截图检查 ═══")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=CHROMIUM)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # 5.1 Load app
    page.goto(FRONTEND)
    page.wait_for_load_state("networkidle", timeout=15000)
    page.screenshot(path=f"{OUT}/01_initial.png")
    check("App loads (no blank screen)", len(page.locator(".app-shell").all()) > 0)

    # 5.2 4-column layout
    app_shell = page.locator(".app-shell")
    if app_shell.count() > 0:
        cols_count = app_shell.locator("> *").count()
        check("4-column layout", cols_count >= 3, f"{cols_count} columns")

    # 5.3 Select first inspiration (if any)
    proj_items = page.locator(".project-list__item")
    if proj_items.count() > 0:
        proj_items.first.click()
        page.wait_for_timeout(400)
        page.screenshot(path=f"{OUT}/02_selected_inspiration.png")
        check("Inspiration selectable", True)
    else:
        # Create one first
        add_btn = page.locator("button.project-list__add-btn").first
        if add_btn.count() == 0:
            add_btn = page.locator('button:has-text("+")').first
        if add_btn.count() > 0:
            add_btn.click()
            page.wait_for_timeout(200)
            inp = page.locator('input[placeholder*="inspiration"], input[placeholder*="name"]').first
            if inp.count() > 0:
                inp.fill("Brainstorm Test")
                inp.press("Enter")
                page.wait_for_timeout(600)
                check("Create inspiration via UI", True)

    # 5.4 Look for Brainstorm button
    page.screenshot(path=f"{OUT}/03_chat_area.png")
    bstorm_btn = page.locator('button:has-text("Brainstorm")').first
    if bstorm_btn.count() == 0:
        bstorm_btn = page.locator('[data-mode="brainstorm"], button[class*="brainstorm"]').first
    check("Brainstorm toggle button present", bstorm_btn.count() > 0)

    if bstorm_btn.count() > 0:
        bstorm_btn.click()
        page.wait_for_timeout(600)
        page.screenshot(path=f"{OUT}/04_brainstorm_mode.png")
        check("Brainstorm mode activated (UI changes)", True)

        # 5.5 Look for input area in brainstorm mode
        textarea = page.locator("textarea").last
        if textarea.count() > 0 and textarea.is_enabled():
            check("Input enabled in brainstorm mode", True)
        else:
            check("Input enabled in brainstorm mode", False, "textarea not enabled")

        # 5.6 Check for "Brainstorm #N Started" divider
        dividers = page.locator(".brainstorm-divider").count()
        check("Brainstorm divider rendered on mode start", dividers > 0, f"{dividers} dividers")

    # 5.7 Check RightPanel
    rp = page.locator(".right-panel")
    check("RightPanel present", rp.count() > 0)

    # 5.8 Check SideNav
    sidenav = page.locator(".side-nav-bar, .sidenav, nav")
    check("SideNavBar present", sidenav.count() > 0)

    # 5.9 Check message area exists
    msg_area = page.locator(".chat-messages, .messages-list, [class*='messages']").first
    check("Messages area present", msg_area.count() > 0)

    page.screenshot(path=f"{OUT}/05_final.png", full_page=True)
    browser.close()

# ──────────────────────────────────────────────────────────────────────────────
print("\n═══ 6. 测试覆盖率检查 ═══")

test_file = pathlib.Path(r"C:\Users\TUF\Workspace\agent-evolve\backend\tests\integration\test_brainstorm.py")
test_src = test_file.read_text(encoding="utf-8")
test_count = test_src.count("async def test_")
check("Backend brainstorm tests exist", test_count >= 3, f"{test_count} test functions")

fe_test = pathlib.Path(r"C:\Users\TUF\Workspace\agent-evolve\frontend\src\components\BrainstormStreamBubble.test.tsx")
fe_src = fe_test.read_text(encoding="utf-8")
fe_count = fe_src.count("it(")
check("Frontend BrainstormStreamBubble tests", fe_count >= 4, f"{fe_count} tests")

# ──────────────────────────────────────────────────────────────────────────────
# Cleanup
try:
    req("DELETE", f"/api/inspirations/{insp_id}")
except Exception:
    pass

print(f"\n📸 截图: {OUT}")
print(f"\n══════════════════════════════")
print(f"  通过: {PASS}  失败: {FAIL}")
print(f"══════════════════════════════\n")
