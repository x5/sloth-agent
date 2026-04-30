// ---- Tauri invoke with browser fallback ----

let tauriAvailable = true;

async function call<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  if (tauriAvailable) {
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      return await invoke<T>(cmd, args);
    } catch {
      tauriAvailable = false;
    }
  }
  return httpFallback<T>(cmd, args);
}

// ---- Declarative route table ----

const BACKEND = "http://127.0.0.1:8000";

type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

interface RouteConfig {
  method: HttpMethod;
  url: (args: Record<string, unknown>) => string;
  body?: (args: Record<string, unknown>) => unknown;
  voidOn204?: boolean;
}

const routes: Record<string, RouteConfig> = {
  // ---- Inspiration CRUD ----
  list_inspirations: {
    method: "GET",
    url: (a) => `${BACKEND}/api/inspirations?query=${encodeURIComponent((a.query as string) || "")}`,
  },
  create_inspiration: {
    method: "POST",
    url: () => `${BACKEND}/api/inspirations`,
    body: (a) => ({ name: a.name }),
  },
  get_inspiration: {
    method: "GET",
    url: (a) => `${BACKEND}/api/inspirations/${a.id}`,
  },
  delete_inspiration: {
    method: "DELETE",
    url: (a) => `${BACKEND}/api/inspirations/${a.id}`,
    voidOn204: true,
  },

  // ---- LLM Config CRUD ----
  list_llm_configs: {
    method: "GET",
    url: () => `${BACKEND}/api/settings/llm`,
  },
  create_llm_config: {
    method: "POST",
    url: () => `${BACKEND}/api/settings/llm`,
    body: (a) => a.req,
  },
  update_llm_config: {
    method: "PATCH",
    url: (a) => `${BACKEND}/api/settings/llm/${a.id}`,
    body: (a) => a.req,
  },
  delete_llm_config: {
    method: "DELETE",
    url: (a) => `${BACKEND}/api/settings/llm/${a.id}`,
    voidOn204: true,
  },
  set_default_llm: {
    method: "PUT",
    url: (a) => `${BACKEND}/api/settings/llm/${a.id}/default`,
  },
  test_llm: {
    method: "POST",
    url: (a) => `${BACKEND}/api/settings/llm/${a.id}/test`,
  },

  // ---- Agent Template CRUD ----
  list_agent_templates: {
    method: "GET",
    url: () => `${BACKEND}/api/settings/agents`,
  },
  update_agent_template: {
    method: "PATCH",
    url: (a) => `${BACKEND}/api/settings/agents/${a.id}`,
    body: (a) => a.req,
  },

  // ---- Team Agent Management ----
  list_agents: {
    method: "GET",
    url: (a) => `${BACKEND}/api/inspirations/${a.inspirationId}/agents`,
  },
  add_agent_to_team: {
    method: "POST",
    url: (a) => `${BACKEND}/api/inspirations/${a.inspirationId}/agents`,
    body: (a) => ({ template_id: a.templateId }),
  },
  update_agent: {
    method: "PATCH",
    url: (a) => `${BACKEND}/api/agents/${a.agentId}`,
    body: (a) => ({ model: a.model }),
  },
  remove_agent_from_team: {
    method: "DELETE",
    url: (a) => `${BACKEND}/api/inspirations/${a.inspirationId}/agents/${a.agentId}`,
    voidOn204: true,
  },

  // ---- Chat ----
  send_chat_message: {
    method: "POST",
    url: (a) => `${BACKEND}/api/inspirations/${a.inspirationId}/chat`,
    body: (a) => ({
      content: a.content,
      mode: a.mode || "chat",
      brainstorm_session_id: a.brainstormSessionId || null,
    }),
  },
  get_messages: {
    method: "GET",
    url: (a) => {
      const params = new URLSearchParams();
      if (a.limit) params.set("limit", String(a.limit));
      if (a.before) params.set("before", String(a.before));
      if (a.brainstormSessionId) params.set("brainstorm_session_id", String(a.brainstormSessionId));
      return `${BACKEND}/api/inspirations/${a.inspirationId}/messages?${params}`;
    },
  },

  // ---- Brainstorm ----
  create_brainstorm_session: {
    method: "POST",
    url: (a) => `${BACKEND}/api/inspirations/${a.inspirationId}/brainstorm-sessions`,
    body: (a) => ({ title: a.title }),
  },
  list_brainstorm_sessions: {
    method: "GET",
    url: (a) => `${BACKEND}/api/inspirations/${a.inspirationId}/brainstorm-sessions`,
  },
  get_brainstorm_session: {
    method: "GET",
    url: (a) => `${BACKEND}/api/brainstorm-sessions/${a.sessionId}`,
  },
  update_brainstorm_session: {
    method: "PATCH",
    url: (a) => `${BACKEND}/api/brainstorm-sessions/${a.sessionId}`,
    body: (a) => a.data || {},
  },
};

export const ROUTE_KEYS = Object.keys(routes);

async function httpFallback<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  const route = routes[cmd];
  if (!route) throw new Error(`Unknown command: ${cmd}`);

  const a = args || {};
  const fetchOpts: RequestInit = { method: route.method };
  if (route.body) {
    fetchOpts.headers = { "Content-Type": "application/json" };
    fetchOpts.body = JSON.stringify(route.body(a));
  }

  const res = await fetch(route.url(a), fetchOpts);
  if (route.voidOn204 && res.status === 204) return undefined as T;
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `${cmd} failed (${res.status})`);
  }
  return res.json();
}

// ---- Types ----

export interface Inspiration {
  id: string;
  name: string;
  agent_count: number;
  latest_message_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LLMConfig {
  id: string;
  provider: string;
  model: string;
  api_key: string;
  base_url: string;
  api_format: string;
  is_default: boolean;
  created_at: string;
}

export interface AgentTemplate {
  id: string;
  name: string;
  role: string;
  default_model: string;
  auto_join: boolean;
  system_prompt: string;
  created_at: string;
}

export interface Message {
  id: string;
  inspiration_id: string;
  agent_id: string | null;
  role: string;
  content: string;
  created_at: string;
  agent_name: string | null;
  agent_number: number | null;
  agent_model: string | null;
  mode: string;
  brainstorm_session_id: string | null;
}

export interface BrainstormSession {
  id: string;
  inspiration_id: string;
  title: string;
  status: string;
  sandbox_path: string;
  max_messages: number;
  cooldown_seconds: number;
  message_count: number;
  summary: string | null;
  started_by: string | null;
  notification_sent: boolean;
  created_at: string;
  ended_at: string | null;
  file_tree: FileTreeEntry[];
}

export interface FileTreeEntry {
  name: string;
  path: string;
  type: "file" | "directory";
  size: number;
}

// ---- Inspiration CRUD ----

export async function createInspiration(name: string): Promise<Inspiration> {
  return call<Inspiration>("create_inspiration", { name });
}

export async function listInspirations(query?: string): Promise<Inspiration[]> {
  return call<Inspiration[]>("list_inspirations", { query: query || null });
}

export async function getInspiration(id: string): Promise<Inspiration> {
  return call<Inspiration>("get_inspiration", { id });
}

export async function deleteInspiration(id: string): Promise<void> {
  return call<void>("delete_inspiration", { id });
}

// ---- LLM Config CRUD ----

export async function listLLMConfigs(): Promise<LLMConfig[]> {
  return call<LLMConfig[]>("list_llm_configs");
}

export async function createLLMConfig(req: {
  provider: string;
  model: string;
  api_key: string;
  base_url: string;
  api_format?: string;
}): Promise<LLMConfig> {
  return call<LLMConfig>("create_llm_config", { req });
}

export async function updateLLMConfig(
  id: string,
  req: {
    provider?: string;
    model?: string;
    api_key?: string;
    base_url?: string;
    api_format?: string;
  }
): Promise<LLMConfig> {
  return call<LLMConfig>("update_llm_config", { id, req });
}

export async function deleteLLMConfig(id: string): Promise<void> {
  return call<void>("delete_llm_config", { id });
}

export async function setDefaultLLM(id: string): Promise<LLMConfig> {
  return call<LLMConfig>("set_default_llm", { id });
}

export interface LLMTestResult {
  ok: boolean;
  latency_ms: number;
  status_code?: number;
  error?: string;
  model?: string;
}

export async function testLLMConnection(id: string): Promise<LLMTestResult> {
  return call<LLMTestResult>("test_llm", { id });
}

// ---- Agent Template CRUD ----

export async function listAgentTemplates(): Promise<AgentTemplate[]> {
  return call<AgentTemplate[]>("list_agent_templates");
}

export async function updateAgentTemplate(
  id: string,
  req: {
    name?: string;
    default_model?: string;
    system_prompt?: string;
    auto_join?: boolean;
  }
): Promise<AgentTemplate> {
  return call<AgentTemplate>("update_agent_template", { id, req });
}

// ---- Agent Team Management ----

export interface TeamAgent {
  id: string;
  inspiration_id: string;
  template_id: string | null;
  name: string;
  role: string;
  model: string;
  status: string;
  joined_at: string;
}

export async function listTeamAgents(inspirationId: string): Promise<TeamAgent[]> {
  return call<TeamAgent[]>("list_agents", { inspirationId });
}

export async function addAgentToTeam(inspirationId: string, templateId: string): Promise<TeamAgent> {
  return call<TeamAgent>("add_agent_to_team", { inspirationId, templateId });
}

export async function updateTeamAgent(agentId: string, model: string): Promise<TeamAgent> {
  return call<TeamAgent>("update_agent", { agentId, model });
}

export async function removeAgentFromTeam(inspirationId: string, agentId: string): Promise<void> {
  return call<void>("remove_agent_from_team", { inspirationId, agentId });
}

// ---- Chat ----

export async function sendChatMessage(
  inspirationId: string,
  content: string,
  opts?: { mode?: string; brainstormSessionId?: string }
): Promise<Message> {
  return call<Message>("send_chat_message", {
    inspirationId,
    content,
    mode: opts?.mode || "chat",
    brainstormSessionId: opts?.brainstormSessionId || null,
  });
}

export async function getMessages(
  inspirationId: string,
  limit?: number,
  before?: string | null,
  brainstormSessionId?: string | null,
): Promise<Message[]> {
  return call<Message[]>("get_messages", {
    inspirationId,
    limit: limit || 50,
    before: before || null,
    brainstormSessionId: brainstormSessionId || null,
  });
}

// ---- Brainstorm ----

export async function createBrainstormSession(
  inspirationId: string,
  title: string,
): Promise<BrainstormSession> {
  return call<BrainstormSession>("create_brainstorm_session", { inspirationId, title });
}

export async function listBrainstormSessions(
  inspirationId: string,
): Promise<BrainstormSession[]> {
  return call<BrainstormSession[]>("list_brainstorm_sessions", { inspirationId });
}

export async function getBrainstormSession(
  sessionId: string,
): Promise<BrainstormSession> {
  return call<BrainstormSession>("get_brainstorm_session", { sessionId });
}

export async function updateBrainstormSession(
  sessionId: string,
  data: { title?: string; status?: string },
): Promise<BrainstormSession> {
  return call<BrainstormSession>("update_brainstorm_session", { sessionId, data });
}
