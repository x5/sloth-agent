"""Iter-6 review script: API smoke tests (no browser required).

Tests all Iter-5 endpoints + new Iter-6 endpoints:
  POST /connect, POST /inject, DELETE /connect
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request

BACKEND = "http://127.0.0.1:8080"
_pass = 0
_fail = 0


def req(method, path, body=None, timeout=8):
    url = BACKEND + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    r = urllib.request.urlopen(
        urllib.request.Request(url, data=data, headers=headers, method=method),
        timeout=timeout,
    )
    return json.loads(r.read())


def check(label, ok, detail=""):
    global _pass, _fail
    mark = "✅" if ok else "❌"
    print(f"  {mark} {label}" + (f" — {detail}" if detail else ""))
    if ok:
        _pass += 1
    else:
        _fail += 1
    return ok


# ─── Section 1: Iter-5 API smoke ────────────────────────────────────────────
print("\n═══ 1. Iter-5 基础 API ═══")

insp = req("POST", "/api/inspirations", {"name": "Iter6-Review"})
insp_id = insp["id"]
check("POST /inspirations → 201", bool(insp_id), f"id={insp_id[:8]}…")

templates = req("GET", "/api/settings/agents")
check("GET /settings/agents has templates", len(templates) > 0, f"{len(templates)} templates")

if templates:
    try:
        # Get agents already auto-joined on inspiration creation
        existing_agents = req("GET", f"/api/inspirations/{insp_id}/agents")
        existing_template_ids = {a["template_id"] for a in existing_agents}

        # Find templates not yet in the inspiration
        available = [t for t in templates if t["id"] not in existing_template_ids]

        if available:
            ag1 = req("POST", f"/api/inspirations/{insp_id}/agents", {"template_id": available[0]["id"]})
            check("Agent added to team", bool(ag1["id"]))
        else:
            # All templates were auto-joined — verify they exist
            check("Agents auto-joined on create", len(existing_agents) > 0, f"{len(existing_agents)} agents")
    except urllib.error.HTTPError as e:
        check("Agents in team", False, f"HTTP {e.code}")

sess = req("POST", f"/api/inspirations/{insp_id}/brainstorm-sessions", {"title": "Iter6 Test"})
sess_id = sess["id"]
check("POST /brainstorm-sessions → 201", bool(sess_id))
check("Session status = active", sess["status"] == "active", sess["status"])

sessions = req("GET", f"/api/inspirations/{insp_id}/brainstorm-sessions")
check("GET /brainstorm-sessions returns list", len(sessions) == 1)

got = req("GET", f"/api/brainstorm-sessions/{sess_id}")
check("GET /brainstorm-sessions/{id} returns session", got["id"] == sess_id)

upd = req("PATCH", f"/api/brainstorm-sessions/{sess_id}", {"title": "Updated Title"})
check("PATCH /brainstorm-sessions updates title", upd["title"] == "Updated Title")

# ─── Section 2: Iter-6 persistent connection API ─────────────────────────────
print("\n═══ 2. Iter-6 持久连接 API ═══")

# 2a. connect nonexistent session → 404
try:
    req("POST", "/api/brainstorm-sessions/no-such-id/connect")
    check("POST /connect nonexistent → 404", False, "should have raised")
except urllib.error.HTTPError as e:
    check("POST /connect nonexistent → 404", e.code == 404, f"HTTP {e.code}")

# 2b. ended session → 400
ended = req("POST", f"/api/inspirations/{insp_id}/brainstorm-sessions", {"title": "Ended"})
req("PATCH", f"/api/brainstorm-sessions/{ended['id']}", {"status": "ended"})
try:
    req("POST", f"/api/brainstorm-sessions/{ended['id']}/connect")
    check("POST /connect ended session → 400", False, "should have raised")
except urllib.error.HTTPError as e:
    check("POST /connect ended session → 400", e.code == 400, f"HTTP {e.code}")

# 2c. inject without active connection → 400
try:
    req("POST", f"/api/brainstorm-sessions/{sess_id}/inject", {"content": "hello"})
    check("POST /inject without connection → 400", False, "should have raised")
except urllib.error.HTTPError as e:
    check("POST /inject without connection → 400", e.code == 400, f"HTTP {e.code}")

# 2d. inject nonexistent session → 404
try:
    req("POST", "/api/brainstorm-sessions/no-such-id/inject", {"content": "hi"})
    check("POST /inject nonexistent → 404", False, "should have raised")
except urllib.error.HTTPError as e:
    check("POST /inject nonexistent → 404", e.code == 404, f"HTTP {e.code}")

# 2e. DELETE /connect on idle session → 200
delete_req = urllib.request.Request(
    f"{BACKEND}/api/brainstorm-sessions/{sess_id}/connect", method="DELETE"
)
try:
    r = urllib.request.urlopen(delete_req, timeout=5)
    check("DELETE /connect idle session → 200", r.status == 200)
except urllib.error.HTTPError as e:
    check("DELETE /connect idle session", False, f"HTTP {e.code}")

# 2f. POST /connect on active session — just verify 200 status
print("\n  Checking POST /connect returns 200…")
import socket, ssl
host = "127.0.0.1"
port = 8080
raw_req = (
    f"POST /api/brainstorm-sessions/{sess_id}/connect HTTP/1.1\r\n"
    f"Host: {host}:{port}\r\n"
    f"Connection: close\r\n\r\n"
)
try:
    sock = socket.create_connection((host, port), timeout=3)
    sock.sendall(raw_req.encode())
    response = b""
    while True:
        chunk = sock.recv(512)
        if not chunk:
            break
        response += chunk
        if b"\r\n\r\n" in response:
            break
    sock.close()
    status_line = response.split(b"\r\n")[0].decode()
    status_code = int(status_line.split(" ")[1]) if " " in status_line else 0
    check("POST /connect active session → 200", status_code == 200, status_line)
    # Disconnect and give SQLite time to release the connection
    time.sleep(0.5)
    try:
        delete_close = urllib.request.Request(
            f"{BACKEND}/api/brainstorm-sessions/{sess_id}/connect", method="DELETE"
        )
        urllib.request.urlopen(delete_close, timeout=3)
    except Exception:
        pass
    time.sleep(0.5)  # Wait for DB cleanup
except Exception as ex:
    check("POST /connect active session → 200", False, str(ex))

# ─── Section 3: OpenAPI schema — MessageResponse fields ────────────────────
print("\n═══ 3. MessageResponse 字段验证 ═══")
try:
    spec = req("GET", "/openapi.json")
    schemas = spec.get("components", {}).get("schemas", {})
    msg_schema = schemas.get("MessageResponse", schemas.get("Message", {}))
    props = msg_schema.get("properties", {})
    fields = ["brainstorm_session_id", "parent_message_id", "round", "intent", "truncated"]
    found = [f for f in fields if f in props]
    check(f"MessageResponse has all 5 brainstorm fields", len(found) == 5, str(found))
except Exception as e:
    check("OpenAPI schema accessible", False, str(e))

# ─── Summary ─────────────────────────────────────────────────────────────────
print(f"\n═══ 结果 ═══")
print(f"  ✅ passed: {_pass}   ❌ failed: {_fail}")
sys.exit(0 if _fail == 0 else 1)
