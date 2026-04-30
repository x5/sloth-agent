import { create } from "zustand";
import * as api from "../api/client";
import type { BrainstormSession } from "../api/client";

interface BrainstormState {
  sessions: BrainstormSession[];
  activeId: string | null;
  brainstormMode: boolean;
  loading: boolean;

  // High-level actions (components should use these)
  fetchAll: (inspirationId: string) => Promise<void>;
  startBrainstorm: (inspirationId: string) => Promise<void>;
  stopBrainstorm: () => void;
  activateSession: (sessionId: string) => Promise<void>;
  endSession: (sessionId: string) => Promise<void>;

  // View-only (for sidebar search, no status/mode change)
  setActive: (id: string | null) => void;

  // Internal (used by startBrainstorm)
  refreshSession: (sessionId: string) => Promise<void>;
}

export const useBrainstormStore = create<BrainstormState>((set, get) => ({
  sessions: [],
  activeId: null,
  brainstormMode: false,
  loading: false,

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
    set({ brainstormMode: false, activeId: null });
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
}));
