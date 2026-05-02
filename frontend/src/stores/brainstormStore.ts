import { create } from "zustand";

import * as api from "../api/client";
import type { BrainstormSession, Message } from "../api/client";

const BACKEND = "http://127.0.0.1:8080";

type SetState = (partial: Partial<BrainstormState> | ((s: BrainstormState) => Partial<BrainstormState>)) => void;
type GetState = () => BrainstormState;

// Abort controllers for legacy one-shot discussion and new persistent connection
let _abortController: AbortController | null = null;
let _persistentController: AbortController | null = null;

function _handleSSEEvent(
  event: string,
  data: Record<string, unknown>,
  set: SetState,
  get: GetState,
  persistent = false,
) {
  switch (event) {
    case "agent_start": {
      set({
        activeAgentId: data.agent_id as string,
        activeAgentName: data.agent_name as string,
        activeAgentNumber: (data.agent_number as number) ?? null,
        streamingContent: "",
      });
      break;
    }
    case "agent_token": {
      const token = data.token as string;
      set((s) => ({
        activeAgentId: data.agent_id as string,
        activeAgentName: data.agent_name as string,
        streamingContent: (s.streamingContent || "") + token,
      }));
      break;
    }
    case "message_done": {
      const agentId = data.agent_id as string;
      const fullContent = data.full_content as string;
      const messageId = data.message_id as string;
      const agentName = data.agent_name as string | null;
      const agentNumber = (data.agent_number as number) ?? null;

      const msg: Message = {
        id: messageId,
        inspiration_id: get().activeId || "",
        agent_id: agentId,
        role: "agent",
        content: fullContent,
        created_at: new Date().toISOString(),
        agent_name: agentName,
        agent_number: agentNumber,
        agent_model: null,
        mode: "brainstorm",
        brainstorm_session_id: get().activeId,
        parent_message_id: (data.parent_message_id as string) || null,
        round: (data.round as number) || 1,
        intent: null,
        truncated: false,
      };

      set((s) => ({
        discussionMessages: [...s.discussionMessages, msg],
        activeAgentId: null,
        activeAgentName: null,
        activeAgentNumber: null,
        streamingContent: "",
      }));
      break;
    }
    case "discussion_end": {
      // In persistent mode the connection stays open 鈥?only mark agents as idle
      set({ discussionActive: false, activeAgentId: null, activeAgentName: null, activeAgentNumber: null, streamingContent: "" });
      break;
    }
    case "agent_pass": {
      set({ activeAgentId: null, activeAgentName: null, activeAgentNumber: null, streamingContent: "" });
      break;
    }
    case "max_reached": {
      console.warn("Brainstorm hit message limit:", data.limit);
      set({ discussionActive: false, activeAgentId: null, activeAgentName: null, activeAgentNumber: null, streamingContent: "" });
      break;
    }
    case "error": {
      console.error("SSE error:", data.error);
      set({ discussionActive: false, activeAgentId: null, activeAgentName: null, activeAgentNumber: null, streamingContent: "" });
      break;
    }
    // ---- Iter-6 persistent-mode events ----
    case "user_message": {
      // Backend confirmed the user message. Replace temp message or append.
      const msgId = data.message_id as string;
      const content = data.content as string;
      const msg: Message = {
        id: msgId,
        inspiration_id: get().activeId || "",
        agent_id: null,
        role: "human",
        content,
        created_at: new Date().toISOString(),
        agent_name: null,
        agent_number: null,
        agent_model: null,
        mode: "brainstorm",
        brainstorm_session_id: get().activeId,
        parent_message_id: null,
        round: 1,
        intent: null,
        truncated: false,
      };
      set((s) => {
        const msgs = [...s.discussionMessages];
        // Replace the newest optimistic temp-human message if it exists
        const tempIdx = msgs.reduce(
          (found, m, i) => (m.role === "human" && m.id.startsWith("temp-") ? i : found),
          -1,
        );
        if (tempIdx >= 0) {
          msgs[tempIdx] = msg;
        } else {
          msgs.push(msg);
        }
        return { discussionMessages: msgs, discussionActive: true };
      });
      break;
    }
    case "round_end": {
      // Informational 鈥?no state change needed
      break;
    }
    case "heartbeat": {
      // Keep-alive ping 鈥?no-op
      break;
    }
  }
}

/** Background SSE reader for persistent connections. */
async function _startPersistentReading(
  res: Response,
  set: SetState,
  get: GetState,
) {
  try {
    const reader = res.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ") && currentEvent) {
          try {
            const data = JSON.parse(line.slice(6));
            _handleSSEEvent(currentEvent, data, set, get, /* persistent */ true);
          } catch {
            // skip malformed JSON
          }
          currentEvent = "";
        }
      }
    }
  } catch (e) {
    if ((e as Error).name !== "AbortError") {
      console.error("Persistent SSE error:", e);
    }
  } finally {
    set({ discussionConnected: false, discussionActive: false, activeAgentId: null, activeAgentName: null, activeAgentNumber: null, streamingContent: "" });
    _persistentController = null;
  }
}

interface BrainstormState {
  sessions: BrainstormSession[];
  activeId: string | null;
  brainstormMode: boolean;
  loading: boolean;

  // Discussion state (shared between legacy and persistent modes)
  discussionActive: boolean;
  activeAgentId: string | null;
  activeAgentName: string | null;
  activeAgentNumber: number | null;
  discussionMessages: Message[];
  streamingContent: string;

  // Iter-6: persistent connection state
  discussionConnected: boolean;
  replyingToId: string | null;
  replyingToContent: string | null;

  // High-level actions
  fetchAll: (inspirationId: string) => Promise<void>;
  startBrainstorm: (inspirationId: string) => Promise<void>;
  stopBrainstorm: () => void;
  activateSession: (sessionId: string) => Promise<void>;
  endSession: (sessionId: string) => Promise<void>;

  // View-only
  setActive: (id: string | null) => void;

  // Iter-6: persistent connection methods
  connectSession: (sessionId: string) => Promise<void>;
  disconnectSession: () => void;
  injectMessage: (sessionId: string, content: string, replyToMessageId?: string) => Promise<void>;
  setReplyingTo: (id: string | null, content: string | null) => void;

  // @deprecated (Iter-7 鍒犻櫎): use connectSession + injectMessage instead
  startDiscussion: (sessionId: string, content: string, replyToMessageId?: string) => Promise<void>;
  // @deprecated (Iter-7 鍒犻櫎): use disconnectSession instead
  stopDiscussion: () => void;

  // Internal
  refreshSession: (sessionId: string) => Promise<void>;
}

export const useBrainstormStore = create<BrainstormState>((set, get) => ({
  sessions: [],
  activeId: null,
  brainstormMode: false,
  loading: false,

  discussionActive: false,
  activeAgentId: null,
  activeAgentName: null,
  activeAgentNumber: null,
  discussionMessages: [],
  streamingContent: "",

  discussionConnected: false,
  replyingToId: null,
  replyingToContent: null,

  fetchAll: async (inspirationId: string) => {
    set({ loading: true });
    try {
      const sessions = await api.listBrainstormSessions(inspirationId);
      set({ sessions });
      const current = get().activeId;
      if (current && !sessions.find((s) => s.id === current)) {
        set({ activeId: sessions[0]?.id ?? null });
      }
    } finally {
      set({ loading: false });
    }
  },

  startBrainstorm: async (inspirationId: string) => {
    const { sessions } = get();
    const nextNum = sessions.length + 1;
    const session = await api.createBrainstormSession(inspirationId, `Brainstorm #${nextNum}`);
    set((s) => ({
      sessions: [session, ...s.sessions],
      activeId: session.id,
      brainstormMode: true,
    }));
  },

  stopBrainstorm: () => {
    // Abort legacy discussion
    if (_abortController) {
      _abortController.abort();
      _abortController = null;
    }
    // Abort persistent connection
    if (_persistentController) {
      _persistentController.abort();
      _persistentController = null;
    }
    const { activeId } = get();
    if (activeId) {
      fetch(`${BACKEND}/api/brainstorm-sessions/${activeId}/connect`, { method: "DELETE" }).catch(() => {});
    }
    set({
      brainstormMode: false,
      activeId: null,
      discussionConnected: false,
      discussionActive: false,
      activeAgentId: null,
      activeAgentName: null,
      activeAgentNumber: null,
      streamingContent: "",
      replyingToId: null,
      replyingToContent: null,
    });
  },

  activateSession: async (sessionId: string) => {
    const { activeId } = get();
    if (activeId && activeId !== sessionId) {
      await api.updateBrainstormSession(activeId, { status: "ended" });
    }
    await api.updateBrainstormSession(sessionId, { status: "active" });
    set((s) => ({
      sessions: s.sessions.map((ses) => {
        if (ses.id === sessionId) return { ...ses, status: "active", ended_at: null };
        if (ses.id === activeId) return { ...ses, status: "ended", ended_at: new Date().toISOString() };
        return ses;
      }),
      activeId: sessionId,
      brainstormMode: true,
    }));
  },

  endSession: async (sessionId: string) => {
    await api.updateBrainstormSession(sessionId, { status: "ended" });
    set((s) => ({
      sessions: s.sessions.map((ses) =>
        ses.id === sessionId ? { ...ses, status: "ended", ended_at: new Date().toISOString() } : ses
      ),
      activeId: s.activeId === sessionId ? null : s.activeId,
      brainstormMode: s.activeId === sessionId ? false : s.brainstormMode,
    }));
  },

  setActive: (id) => set({ activeId: id }),

  refreshSession: async (sessionId: string) => {
    const updated = await api.getBrainstormSession(sessionId);
    set((s) => ({
      sessions: s.sessions.map((ses) => ses.id === sessionId ? updated : ses),
    }));
  },

  // ---- Iter-6: Persistent connection ----

  connectSession: async (sessionId: string) => {
    // Abort any existing persistent connection
    if (_persistentController) {
      _persistentController.abort();
    }
    _persistentController = new AbortController();

    const res = await fetch(`${BACKEND}/api/brainstorm-sessions/${sessionId}/connect`, {
      method: "POST",
      signal: _persistentController.signal,
    });

    if (!res.ok) {
      const err = await res.text();
      _persistentController = null;
      throw new Error(err || `Connect failed (${res.status})`);
    }

    set({ discussionConnected: true, discussionMessages: [] });

    // Start background reading loop (intentionally not awaited)
    _startPersistentReading(res, set, get);
  },

  disconnectSession: () => {
    if (_persistentController) {
      _persistentController.abort();
      _persistentController = null;
    }
    const { activeId } = get();
    if (activeId) {
      fetch(`${BACKEND}/api/brainstorm-sessions/${activeId}/connect`, { method: "DELETE" }).catch(() => {});
    }
    set({
      discussionConnected: false,
      discussionActive: false,
      activeAgentId: null,
      activeAgentName: null,
      activeAgentNumber: null,
      streamingContent: "",
    });
  },

  injectMessage: async (sessionId: string, content: string, replyToMessageId?: string) => {
    const res = await fetch(`${BACKEND}/api/brainstorm-sessions/${sessionId}/inject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, reply_to_message_id: replyToMessageId || null }),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || `Inject failed (${res.status})`);
    }
  },

  setReplyingTo: (id, content) => set({ replyingToId: id, replyingToContent: content }),

  // ---- @deprecated: legacy one-shot SSE (kept until Iter-7) ----

  startDiscussion: async (sessionId: string, content: string, replyToMessageId?: string) => {
    if (_abortController) {
      _abortController.abort();
    }
    _abortController = new AbortController();

    set({ discussionActive: true, discussionMessages: [] });

    try {
      const res = await fetch(`${BACKEND}/api/brainstorm-sessions/${sessionId}/discuss`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, reply_to_message_id: replyToMessageId || null }),
        signal: _abortController.signal,
      });

      if (!res.ok) {
        const err = await res.text();
        throw new Error(err || `SSE failed (${res.status})`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ") && currentEvent) {
            try {
              const data = JSON.parse(line.slice(6));
              _handleSSEEvent(currentEvent, data, set, get);
            } catch {
              // skip malformed JSON
            }
            currentEvent = "";
          }
        }
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") {
        // User aborted 鈥?not an error
      } else {
        console.error("Discussion error:", e);
      }
    } finally {
      _abortController = null;
      set({ discussionActive: false });
      const { activeId } = get();
      if (activeId) {
        get().refreshSession(activeId);
      }
    }
  },

  stopDiscussion: () => {
    if (_abortController) {
      _abortController.abort();
      _abortController = null;
    }
    const { activeId } = get();
    if (activeId) {
      fetch(`${BACKEND}/api/brainstorm-sessions/${activeId}/discuss`, {
        method: "DELETE",
      }).catch(() => {});
    }
    set({ discussionActive: false, activeAgentId: null, activeAgentName: null, activeAgentNumber: null, streamingContent: "" });
  },
}));

