import { create } from "zustand";

import * as api from "../api/client";
import type { TeamAgent, AgentTemplate } from "../api/client";

interface AgentStore {
  teamMembers: TeamAgent[];
  templatePool: AgentTemplate[];
  loading: boolean;

  fetchTeam: (inspirationId: string) => Promise<void>;
  fetchTemplatePool: () => Promise<void>;
  addToTeam: (inspirationId: string, templateId: string) => Promise<void>;
  updateModel: (agentId: string, model: string) => Promise<void>;
  removeFromTeam: (inspirationId: string, agentId: string) => Promise<void>;
}

export const useAgentStore = create<AgentStore>((set) => ({
  teamMembers: [],
  templatePool: [],
  loading: false,

  fetchTeam: async (inspirationId) => {
    set({ loading: true });
    try {
      const data = await api.listTeamAgents(inspirationId);
      set({ teamMembers: data, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchTemplatePool: async () => {
    try {
      const data = await api.listAgentTemplates();
      set({ templatePool: data });
    } catch {
      // pool fetch is best-effort
    }
  },

  addToTeam: async (inspirationId, templateId) => {
    const created = await api.addAgentToTeam(inspirationId, templateId);
    set((state) => ({
      teamMembers: [...state.teamMembers, created],
    }));
  },

  updateModel: async (agentId, model) => {
    const updated = await api.updateTeamAgent(agentId, model);
    set((state) => ({
      teamMembers: state.teamMembers.map((m) =>
        m.id === agentId ? updated : m
      ),
    }));
  },

  removeFromTeam: async (inspirationId, agentId) => {
    await api.removeAgentFromTeam(inspirationId, agentId);
    set((state) => ({
      teamMembers: state.teamMembers.filter((m) => m.id !== agentId),
    }));
  },
}));
