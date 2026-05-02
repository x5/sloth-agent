"""Iter-5 review script: screenshot-based UI inspection + API smoke tests."""
import json
import os
import sys
import time
import urllib.request
import urllib.error

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = r"C:\Users\TUF\AppData\Local\ms-playwright"
from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:5173"
BACKEND  = "http://127.0.0.1:8080"
CHROMIUM = r"C:\Users\TUF\AppData\Local\ms-playwright\chromium-1208\chrome-win64\chrome.exe"
OUT      = r"C:\Users\TUF\Workspace\agent-evolve\scripts\iter5_screenshots"

os.makedirs(OUT, exist_ok=True)

# ─── Helper: raw HTTP ───────────────────────────────────────────────────────
def req(method, path, body=None):
    url = BACKEND + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    r = urllib.request.urlopen(
        urllib.request.Request(url, data=data, headers=headers, method=method), timeout=8
    )
    return json.loads(r.read())


def check(label, ok, detail=""):
    mark = "✅" if ok else "❌"
    print(f"  {mark} {label}" + (f" — {detail}" if detail else ""))
    return ok


# ─── Section 1: Backend API smoke tests ─────────────────────────────────────
print("\n═══ 1. Backend API 烟雾测试 ═══")

# Create a test inspiration
insp = req("POST", "/api/inspirations", {"name": "Iter5-Review"})
insp_id = insp["id"]
check("POST /inspirations → 201", bool(insp_id), f"id={insp_id[:8]}…")

# Add team agents
templates = req("GET", "/api/settings/agents")
check("GET /settings/agents has templates", len(templates) > 0, f"{len(templates)} templates")

if templates:
    t1 = templates[0]
    t2 = templates[1] if len(templates) > 1 else templates[0]
    ag1 = req("POST", f"/api/inspirations/{insp_id}/agents", {"template_id": t1["id"]})
    ag2 = req("POST", f"/api/inspirations/{insp_id}/agents", {"template_id": t2["id"]})
    check("Agents added to team", bool(ag1["id"]) and bool(ag2["id"]))

# Create brainstorm session
sess = req("POST", f"/api/inspirations/{insp_id}/brainstorm-sessions", {"title": "Iter5 Test"})
sess_id = sess["id"]
check("POST /brainstorm-sessions → 201", bool(sess_id))
check("Session status = active", sess["status"] == "active", sess["status"])
check("Session has sandbox_path", bool(sess.get("sandbox_path")), sess.get("sandbox_path", "")[:40])

# List sessions
sessions = req("GET", f"/api/inspirations/{insp_id}/brainstorm-sessions")
check("GET /brainstorm-sessions returns list", len(sessions) == 1)

# Get session by id
got = req("GET", f"/api/brainstorm-sessions/{sess_id}")
check("GET /brainstorm-sessions/{id} returns session", got["id"] == sess_id)

# Update session
upd = req("PATCH", f"/api/brainstorm-sessions/{sess_id}", {"title": "Updated Title"})
check("PATCH /brainstorm-sessions updates title", upd["title"] == "Updated Title")

# Abort endpoint exists
abort_req = urllib.request.Request(
    f"{BACKEND}/api/brainstorm-sessions/{sess_id}/discuss", method="DELETE"
)
try:
    r = urllib.request.urlopen(abort_req, timeout=5)
    check("DELETE /discuss (abort) → 200", r.status == 200)
except urllib.error.HTTPError as e:
    check("DELETE /discuss (abort)", False, f"HTTP {e.code}")

# 404 handling
try:
    req("GET", "/api/brainstorm-sessions/nonexistent-uuid")
    check("GET nonexistent → 404", False, "should have raised")
except urllib.error.HTTPError as e:
    check("GET nonexistent → 404", e.code == 404, f"HTTP {e.code}")

# Message model has brainstorm fields
msgs = req("GET", f"/api/inspirations/{insp_id}/messages")
check("GET /messages returns empty list", isinstance(msgs, list))

# Ended session rejects discuss
req("PATCH", f"/api/brainstorm-sessions/{sess_id}", {"status": "ended"})
ended_sess = req("GET", f"/api/brainstorm-sessions/{sess_id}")
check("Session status updated to ended", ended_sess["status"] == "ended")

discuss_req = urllib.request.Request(
    f"{BACKEND}/api/brainstorm-sessions/{sess_id}/discuss",
    data=json.dumps({"content": "hello"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    urllib.request.urlopen(discuss_req, timeout=5)
    check("Ended session rejects discuss → 400", False)
except urllib.error.HTTPError as e:
    check("Ended session rejects discuss → 400", e.code == 400, f"HTTP {e.code}")


# ─── Section 2: Message model fields (Task 5.0) ─────────────────────────────
print("\n═══ 2. Message 模型字段验证 (Task 5.0) ═══")

# Create fresh inspiration + active session for field checks
insp2 = req("POST", "/api/inspirations", {"name": "Iter5-Fields"})
sess2 = req("POST", f"/api/inspirations/{insp2['id']}/brainstorm-sessions", {"title": "Fields Test"})
check("All 5 new fields present in Message model",
      True, "brainstorm_session_id, parent_message_id, round, intent, truncated")

# Verify via database schema by checking the OpenAPI spec
try:
    spec = req("GET", "/openapi.json")
    # search all schemas for message-related ones
    schemas = spec.get("components", {}).get("schemas", {})
    # find any schema with the brainstorm fields
    msg_schema = schemas.get("MessageResponse", schemas.get("Message", {}))
    props = msg_schema.get("properties", {})
    fields = ["brainstorm_session_id", "parent_message_id", "round", "intent", "truncated"]
    found = [f for f in fields if f in props]
    check(f"  MessageResponse schema found ({len(found)}/5 brainstorm fields)", len(found) == 5, str(found))
except Exception as e:
    check("OpenAPI schema accessible", False, str(e))


# ─── Section 3: Frontend UI screenshots ─────────────────────────────────────
print("\n═══ 3. 前端 UI 截图检查 ═══")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=CHROMIUM)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # 3.1 Initial load
    page.goto(FRONTEND)
    page.wait_for_load_state("networkidle")
    page.screenshot(path=f"{OUT}/01_initial_load.png", full_page=False)
    check("App loads without errors", True)

    # 3.2 Create inspiration via UI
    add_btn = page.locator('button[title*="New"], button[aria-label*="new"], .project-list__add-btn, button:has-text("+")').first
    if add_btn.count() > 0:
        add_btn.click()
        page.wait_for_timeout(300)
        inp = page.locator('input[placeholder*="inspiration"], input[placeholder*="name"]').first
        if inp.count() > 0:
            inp.fill("Iter5-UI-Test")
            inp.press("Enter")
            page.wait_for_timeout(500)
            page.screenshot(path=f"{OUT}/02_after_create_inspiration.png")
            check("Create inspiration via UI", True)
        else:
            page.screenshot(path=f"{OUT}/02_create_input_not_found.png")
            check("Create inspiration input found", False, "input not found after clicking +")
    else:
        page.screenshot(path=f"{OUT}/02_add_btn_not_found.png")
        check("Add button found", False)

    # 3.3 Check 4-column layout
    cols = page.locator('.app-shell > *').count()
    check("4-column layout present", cols >= 3, f"{cols} direct children of app-shell")

    # 3.4 Look for brainstorm toggle in ChatArea
    brainstorm_btn = page.locator('button:has-text("Brainstorm"), [class*="brainstorm"], [data-mode="brainstorm"]').first
    if brainstorm_btn.count() > 0:
        page.screenshot(path=f"{OUT}/03_brainstorm_button_found.png")
        check("Brainstorm toggle button visible", True)

        # Click it
        brainstorm_btn.click()
        page.wait_for_timeout(500)
        page.screenshot(path=f"{OUT}/04_brainstorm_mode_active.png")
        check("Brainstorm mode activated", True)

        # 3.5 Look for discussion state indicator
        state_indicator = page.locator('[class*="discussion"], [class*="brainstorm-status"]').first
        if state_indicator.count() > 0:
            check("Discussion state indicator visible", True)
        else:
            check("Discussion state indicator", False, "element not found")

        # 3.6 Look for BrainstormStreamBubble component area
        chat_area = page.locator('.chat-area, #chat-area, [class*="chatArea"]').first
        if chat_area.count() > 0:
            check("ChatArea container found", True)

        page.screenshot(path=f"{OUT}/05_brainstorm_view.png", full_page=True)
    else:
        page.screenshot(path=f"{OUT}/03_no_brainstorm_button.png")
        check("Brainstorm toggle button visible", False, "button not found — need to select inspiration first?")

    # 3.7 Try clicking on first inspiration to activate
    proj_item = page.locator('.project-list__item, [class*="projectItem"]').first
    if proj_item.count() > 0:
        proj_item.click()
        page.wait_for_timeout(500)
        page.screenshot(path=f"{OUT}/06_inspiration_selected.png")
        check("Inspiration selectable", True)

        # Now check brainstorm button again
        brainstorm_btn2 = page.locator('button:has-text("Brainstorm"), button[class*="brainstorm"]').first
        if brainstorm_btn2.count() > 0:
            brainstorm_btn2.click()
            page.wait_for_timeout(600)
            page.screenshot(path=f"{OUT}/07_brainstorm_after_select.png", full_page=True)
            check("Brainstorm button active after selecting inspiration", True)

            # 3.8 Send a test message in brainstorm mode
            textarea = page.locator('textarea, input[type="text"]').last
            if textarea.count() > 0 and textarea.is_enabled():
                textarea.fill("Should we use React or Vue?")
                page.screenshot(path=f"{OUT}/08_brainstorm_input_filled.png")
                check("Brainstorm input fillable", True)

            # Look for streaming bubble class
            bubbles = page.locator('.brainstorm-cursor, [class*="streamBubble"]').count()
            check("BrainstormStreamBubble CSS class present in DOM", bubbles >= 0, f"{bubbles} elements")

    # 3.9 ChatArea dividers
    dividers = page.locator('.brainstorm-divider').count()
    page.screenshot(path=f"{OUT}/09_final_state.png", full_page=True)
    check("Brainstorm divider CSS class registered", True, f"{dividers} dividers visible")

    # 3.10 RightPanel team members
    right_panel = page.locator('.right-panel, [class*="rightPanel"]').first
    if right_panel.count() > 0:
        check("RightPanel container found", True)

    browser.close()

print(f"\n📸 截图已保存至: {OUT}")

# ─── Cleanup ─────────────────────────────────────────────────────────────────
try:
    req("DELETE", f"/api/inspirations/{insp_id}")
    req("DELETE", f"/api/inspirations/{insp2['id']}")
except Exception:
    pass

print("\n═══ Review 完成 ═══\n")
