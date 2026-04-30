import { create } from "zustand";
import * as api from "../api/client";
import type { BrainstormSession } from "../api/client";

interface BrainstormState {
  sessions: BrainstormSession[];
  activeId: string | null;
  loading: boolean;
  fetchAll: (inspirationId: string) => Promise<void>;
  create: (inspirationId: string, title: string) => Promise<BrainstormSession>;
  setActive: (id: string | null) => void;
}

export const useBrainstormStore = create<BrainstormState>((set, get) => ({
  sessions: [],
  activeId: null,
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

  create: async (inspirationId: string, title: string) => {
    const session = await api.createBrainstormSession(inspirationId, title);
    set((s) => ({ sessions: [session, ...s.sessions], activeId: session.id }));
    return session;
  },

  setActive: (id) => set({ activeId: id }),
}));
