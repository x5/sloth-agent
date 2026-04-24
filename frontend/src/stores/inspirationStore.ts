import { create } from "zustand";
import * as api from "../api/client";
import type { Inspiration } from "../api/client";

interface InspirationState {
  inspirations: Inspiration[];
  activeId: string | null;
  loading: boolean;

  fetchAll: (query?: string) => Promise<void>;
  create: (name: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  setActive: (id: string | null) => void;
}

export const useInspirationStore = create<InspirationState>((set) => ({
  inspirations: [],
  activeId: null,
  loading: false,

  fetchAll: async (query) => {
    set({ loading: true });
    try {
      const data = await api.listInspirations(query);
      set({ inspirations: data, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  create: async (name) => {
    const created = await api.createInspiration(name);
    set((state) => ({
      inspirations: [created, ...state.inspirations],
      activeId: created.id,
    }));
  },

  remove: async (id) => {
    await api.deleteInspiration(id);
    set((state) => {
      const filtered = state.inspirations.filter((i) => i.id !== id);
      return {
        inspirations: filtered,
        activeId: state.activeId === id ? null : state.activeId,
      };
    });
  },

  setActive: (id) => set({ activeId: id }),
}));
