import { create } from "zustand";
import * as api from "../api/client";
import type { BrainstormSession, Message } from "../api/client";

const BACKEND = "http://127.0.0.1:8080";

type SetState = (partial: Partial<BrainstormState> | ((s: BrainstormState) => Partial<BrainstormState>)) => void;
type GetState = () => BrainstormState;

// Active abort controller for the current discussion
let _abortController: AbortController | null = null;

function _handleSSEEvent(event: string, data: Record<string, unknown>, set: SetState, get: GetState) {
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
      set({ discussionActive: false, activeAgentId: null, activeAgentName: null, activeAgentNumber: null, streamingContent: "" });
      break;
    }
    case "agent_pass": {
      // Agent decided it has nothing new to add — clear the streaming bubble
      set({ activeAgentId: null, activeAgentName: null, activeAgentNumber: null, streamingContent: "" });
      break;
    }
    case "error": {
      console.error("SSE error:", data.error);
      break;
    }
  }
}

interface BrainstormState {
  sessions: BrainstormSession[];
  activeId: string | null;
  brainstormMode: boolean;
  loading: boolean;

  // Discussion state
  discussionActive: boolean;
  activeAgentId: string | null;
  activeAgentName: string | null;
  activeAgentNumber: number | null;
  discussionMessages: Message[];
  streamingContent: string;

  // High-level actions (components should use these)
  fetchAll: (inspirationId: string) => Promise<void>;
  startBrainstorm: (inspirationId: string) => Promise<void>;
  stopBrainstorm: () => void;
  activateSession: (sessionId: string) => Promise<void>;
  endSession: (sessionId: string) => Promise<void>;

  // View-only (for sidebar search, no status/mode change)
  setActive: (id: string | null) => void;

  // SSE discussion
  startDiscussion: (sessionId: string, content: string, replyToMessageId?: string) => Promise<void>;
  stopDiscussion: () => void;

  // Internal (used by startBrainstorm)
  refreshSession: (sessionId: string) => Promise<void>;
}

export const useBrainstormStore = create<BrainstormState>((set, get) => ({
  sessions: [],
  activeId: null,
  brainstormMode: false,
  loading: false,

  // Discussion state
  discussionActive: false,
  activeAgentId: null,
  activeAgentName: null,
  activeAgentNumber: null,
  discussionMessages: [],
  streamingContent: "",

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
    // Abort any active discussion first
    if (_abortController) {
      _abortController.abort();
      _abortController = null;
    }
    set({ brainstormMode: false, activeId: null, discussionActive: false, activeAgentId: null, activeAgentName: null, activeAgentNumber: null, streamingContent: "" });
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

  startDiscussion: async (sessionId: string, content: string, replyToMessageId?: string) => {
    // Abort any existing discussion
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
        // User aborted — not an error
      } else {
        console.error("Discussion error:", e);
      }
    } finally {
      _abortController = null;
      set({ discussionActive: false });
      // Refresh session to get updated message_count
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
    // Also tell the backend to abort
    const { activeId } = get();
    if (activeId) {
      fetch(`${BACKEND}/api/brainstorm-sessions/${activeId}/discuss`, {
        method: "DELETE",
      }).catch(() => {});
    }
    set({ discussionActive: false, activeAgentId: null, activeAgentName: null, activeAgentNumber: null, streamingContent: "" });
  },
}));
