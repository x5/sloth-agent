import { create } from "zustand";
import * as api from "../api/client";
import type { LLMConfig } from "../api/client";

interface LLMState {
  configs: LLMConfig[];
  activeId: string | null;
  loading: boolean;

  fetchAll: () => Promise<void>;
  create: (req: {
    provider: string;
    model: string;
    api_key: string;
    base_url: string;
    api_format?: string;
  }) => Promise<void>;
  update: (
    id: string,
    req: {
      provider?: string;
      model?: string;
      api_key?: string;
      base_url?: string;
      api_format?: string;
    }
  ) => Promise<void>;
  remove: (id: string) => Promise<void>;
  setDefault: (id: string) => Promise<void>;
  setActive: (id: string | null) => void;
}

export const useLLMStore = create<LLMState>((set) => ({
  configs: [],
  activeId: null,
  loading: false,

  fetchAll: async () => {
    set({ loading: true });
    try {
      const data = await api.listLLMConfigs();
      set({ configs: data, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  create: async (req) => {
    const created = await api.createLLMConfig(req);
    set((state) => ({
      configs: [...state.configs, created],
      activeId: created.id,
    }));
  },

  update: async (id, req) => {
    const updated = await api.updateLLMConfig(id, req);
    set((state) => ({
      configs: state.configs.map((c) => (c.id === id ? updated : c)),
    }));
  },

  remove: async (id) => {
    await api.deleteLLMConfig(id);
    set((state) => {
      const filtered = state.configs.filter((c) => c.id !== id);
      return {
        configs: filtered,
        activeId: state.activeId === id ? null : state.activeId,
      };
    });
  },

  setDefault: async (id) => {
    await api.setDefaultLLM(id);
    set((state) => ({
      configs: state.configs.map((c) => ({
        ...c,
        is_default: c.id === id,
      })),
    }));
  },

  setActive: (id) => set({ activeId: id }),
}));
