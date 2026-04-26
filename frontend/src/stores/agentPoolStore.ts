import { create } from "zustand";
import * as api from "../api/client";
import type { AgentTemplate } from "../api/client";

interface AgentPoolState {
  templates: AgentTemplate[];
  activeId: string | null;
  loading: boolean;

  fetchAll: () => Promise<void>;
  update: (
    id: string,
    req: {
      name?: string;
      default_model?: string;
      system_prompt?: string;
      auto_join?: boolean;
    }
  ) => Promise<void>;
  setActive: (id: string | null) => void;
}

export const useAgentPoolStore = create<AgentPoolState>((set) => ({
  templates: [],
  activeId: null,
  loading: false,

  fetchAll: async () => {
    set({ loading: true });
    try {
      const data = await api.listAgentTemplates();
      set({ templates: data, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  update: async (id, req) => {
    const updated = await api.updateAgentTemplate(id, req);
    set((state) => ({
      templates: state.templates.map((t) => (t.id === id ? updated : t)),
    }));
  },

  setActive: (id) => set({ activeId: id }),
}));
