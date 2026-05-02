import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/client", () => ({
  BACKEND: "http://127.0.0.1:8080",
  createBrainstormSession: vi.fn(),
  listBrainstormSessions: vi.fn(),
  getBrainstormSession: vi.fn(),
  updateBrainstormSession: vi.fn(),
}));

vi.mock("./agentStore", () => ({
  useAgentStore: {
    getState: () => ({
      setAgentStatus: vi.fn(),
      setAllAgentStatus: vi.fn(),
    }),
  },
}));

function makeSession(id: string) {
  return {
    id,
    inspiration_id: "insp-1",
    title: "Brainstorm #1",
    status: "active",
    sandbox_path: "",
    max_messages: 1000,
    cooldown_seconds: 5,
    message_count: 0,
    summary: null,
    started_by: null,
    notification_sent: false,
    created_at: "2026-05-02T00:00:00.000Z",
    ended_at: null,
    file_tree: [],
  };
}

describe("brainstormStore lifecycle", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.resetModules();
    fetchMock.mockReset();
    fetchMock.mockResolvedValue({ ok: true, text: async () => "" });
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("stopBrainstorm marks active session ended and sends DELETE connect", async () => {
    const { useBrainstormStore } = await import("./brainstormStore");
    useBrainstormStore.setState({
      sessions: [makeSession("sess-1")],
      activeId: "sess-1",
      brainstormMode: true,
    });

    useBrainstormStore.getState().stopBrainstorm();

    const state = useBrainstormStore.getState();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8080/api/brainstorm-sessions/sess-1/connect",
      { method: "DELETE" },
    );
    expect(state.brainstormMode).toBe(false);
    expect(state.activeId).toBeNull();
    expect(state.sessions[0]?.status).toBe("ended");
    expect(state.sessions[0]?.ended_at).toBeTruthy();
  });

  it("disconnectSession marks active session ended and sends DELETE connect", async () => {
    const { useBrainstormStore } = await import("./brainstormStore");
    useBrainstormStore.setState({
      sessions: [makeSession("sess-2")],
      activeId: "sess-2",
      discussionConnected: true,
    });

    useBrainstormStore.getState().disconnectSession();

    const state = useBrainstormStore.getState();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8080/api/brainstorm-sessions/sess-2/connect",
      { method: "DELETE" },
    );
    expect(state.discussionConnected).toBe(false);
    expect(state.sessions[0]?.status).toBe("ended");
    expect(state.sessions[0]?.ended_at).toBeTruthy();
  });
});
