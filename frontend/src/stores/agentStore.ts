import { create } from "zustand";

import * as api from "../api/client";
import type { TeamAgent, AgentTemplate } from "../api/client";

let _statusSyncTimer: ReturnType<typeof setInterval> | null = null;
let _statusSyncFirstPollTimer: ReturnType<typeof setTimeout> | null = null;
let _statusSyncInspirationId: string | null = null;
let _statusSyncRefCount = 0;
let _statusSyncInFlight = false;
const STATUS_SYNC_INTERVAL_MS = 1200;
const STATUS_SYNC_FIRST_POLL_DELAY_MS = 400;
const AGENT_IDLE_GRACE_MS = 10 * 60 * 1000;

const _lastActiveAt = new Map<string, number>();
const _idleTimers = new Map<string, ReturnType<typeof setTimeout>>();

function _clearIdleTimer(agentId: string) {
  const timer = _idleTimers.get(agentId);
  if (timer) {
    clearTimeout(timer);
    _idleTimers.delete(agentId);
  }
}

function _markActive(agentId: string) {
  _lastActiveAt.set(agentId, Date.now());
  _clearIdleTimer(agentId);
}

function _remainingGraceMs(agentId: string): number {
  const ts = _lastActiveAt.get(agentId);
  if (!ts) return 0;
  return Math.max(0, ts + AGENT_IDLE_GRACE_MS - Date.now());
}

function _scheduleIdle(agentId: string, set: (fn: (state: AgentStore) => Partial<AgentStore>) => void, delayMs = AGENT_IDLE_GRACE_MS) {
  _clearIdleTimer(agentId);
  const timer = setTimeout(() => {
    set((state) => ({
      teamMembers: state.teamMembers.map((m) =>
        m.id === agentId ? { ...m, status: "idle" } : m
      ),
    }));
    _idleTimers.delete(agentId);
  }, delayMs);
  _idleTimers.set(agentId, timer);
}

function _normalizeFetchedStatuses(
  fetched: TeamAgent[],
  set: (fn: (state: AgentStore) => Partial<AgentStore>) => void,
): TeamAgent[] {
  return fetched.map((agent) => {
    if (agent.status === "working") {
      _markActive(agent.id);
      return agent;
    }

    const remaining = _remainingGraceMs(agent.id);
    if (remaining > 0) {
      _scheduleIdle(agent.id, set, remaining);
      return { ...agent, status: "working" };
    }

    return agent;
  });
}

interface AgentStore {
  teamMembers: TeamAgent[];
  templatePool: AgentTemplate[];
  loading: boolean;

  fetchTeam: (inspirationId: string) => Promise<void>;
  fetchTemplatePool: () => Promise<void>;
  addToTeam: (inspirationId: string, templateId: string) => Promise<void>;
  updateModel: (agentId: string, model: string) => Promise<void>;
  removeFromTeam: (inspirationId: string, agentId: string) => Promise<void>;
  setAgentStatus: (agentId: string, status: string) => void;
  setAllAgentStatus: (status: string) => void;
  startStatusSync: (inspirationId: string) => Promise<void>;
  stopStatusSync: () => Promise<void>;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  teamMembers: [],
  templatePool: [],
  loading: false,

  fetchTeam: async (inspirationId) => {
    set({ loading: true });
    try {
      const data = await api.listTeamAgents(inspirationId);
      set({ teamMembers: _normalizeFetchedStatuses(data, set), loading: false });
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
    _clearIdleTimer(agentId);
    _lastActiveAt.delete(agentId);
    set((state) => ({
      teamMembers: state.teamMembers.filter((m) => m.id !== agentId),
    }));
  },

  setAgentStatus: (agentId, status) => {
    if (status === "working") {
      _markActive(agentId);
      set((state) => ({
        teamMembers: state.teamMembers.map((m) =>
          m.id === agentId ? { ...m, status: "working" } : m
        ),
      }));
      return;
    }

    if (_remainingGraceMs(agentId) > 0) {
      _scheduleIdle(agentId, set);
      return;
    }

    set((state) => ({
      teamMembers: state.teamMembers.map((m) =>
        m.id === agentId ? { ...m, status: "idle" } : m
      ),
    }));
  },

  setAllAgentStatus: (status) => {
    const members = get().teamMembers;
    if (status === "working") {
      members.forEach((m) => _markActive(m.id));
      set((state) => ({
        teamMembers: state.teamMembers.map((m) => ({ ...m, status: "working" })),
      }));
      return;
    }

    members.forEach((m) => {
      if (_remainingGraceMs(m.id) > 0) {
        _scheduleIdle(m.id, set);
      }
    });
  },

  startStatusSync: async (inspirationId) => {
    _statusSyncRefCount += 1;

    // Optimistically reflect chat start immediately in UI.
    set((state) => {
      const next = state.teamMembers.map((m) => {
        if (m.role !== "lead") return m;
        _markActive(m.id);
        return { ...m, status: "working" };
      });
      return { teamMembers: next };
    });

    const pollOnce = async () => {
      if (_statusSyncInFlight) return;
      _statusSyncInFlight = true;
      try {
        const data = await api.listTeamAgents(inspirationId);
        set({ teamMembers: _normalizeFetchedStatuses(data, set) });
      } finally {
        _statusSyncInFlight = false;
      }
    };

    if (_statusSyncTimer && _statusSyncInspirationId === inspirationId) {
      return;
    }

    if (_statusSyncTimer) {
      clearInterval(_statusSyncTimer);
      _statusSyncTimer = null;
    }
    if (_statusSyncFirstPollTimer) {
      clearTimeout(_statusSyncFirstPollTimer);
      _statusSyncFirstPollTimer = null;
    }

    _statusSyncInspirationId = inspirationId;
    _statusSyncTimer = setInterval(() => {
      void pollOnce();
    }, STATUS_SYNC_INTERVAL_MS);

    // Delay first read slightly to let backend commit working status.
    _statusSyncFirstPollTimer = setTimeout(() => {
      _statusSyncFirstPollTimer = null;
      void pollOnce();
    }, STATUS_SYNC_FIRST_POLL_DELAY_MS);
  },

  stopStatusSync: async () => {
    _statusSyncRefCount = Math.max(0, _statusSyncRefCount - 1);
    if (_statusSyncRefCount > 0) {
      return;
    }

    if (_statusSyncTimer) {
      clearInterval(_statusSyncTimer);
      _statusSyncTimer = null;
    }
    if (_statusSyncFirstPollTimer) {
      clearTimeout(_statusSyncFirstPollTimer);
      _statusSyncFirstPollTimer = null;
    }

    const inspirationId = _statusSyncInspirationId;
    _statusSyncInspirationId = null;
    if (!inspirationId) {
      return;
    }

    // Trailing refresh to catch backend working -> idle commit that may lag stream completion.
    setTimeout(() => {
      void api.listTeamAgents(inspirationId)
        .then((data) => set({ teamMembers: _normalizeFetchedStatuses(data, set) }))
        .catch(() => {});
    }, 250);
  },
}));
