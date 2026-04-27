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

const BACKEND = "http://127.0.0.1:8080";

async function httpFallback<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  let res: Response;
  const baseHeaders: Record<string, string> = { "Content-Type": "application/json" };

  switch (cmd) {
    // ---- Inspiration CRUD ----
    case "list_inspirations": {
      const q = (args?.query as string) || "";
      res = await fetch(`${BACKEND}/api/inspirations?query=${encodeURIComponent(q)}`);
      break;
    }
    case "create_inspiration":
      res = await fetch(`${BACKEND}/api/inspirations`, {
        method: "POST", headers: baseHeaders,
        body: JSON.stringify({ name: args?.name }),
      });
      break;
    case "get_inspiration":
      res = await fetch(`${BACKEND}/api/inspirations/${args?.id}`);
      break;
    case "delete_inspiration":
      res = await fetch(`${BACKEND}/api/inspirations/${args?.id}`, { method: "DELETE" });
      if (res.status === 204) return undefined as T;
      break;

    // ---- LLM Config CRUD ----
    case "list_llm_configs":
      res = await fetch(`${BACKEND}/api/settings/llm`);
      break;
    case "create_llm_config":
      res = await fetch(`${BACKEND}/api/settings/llm`, {
        method: "POST", headers: baseHeaders,
        body: JSON.stringify(args?.req),
      });
      break;
    case "update_llm_config":
      res = await fetch(`${BACKEND}/api/settings/llm/${args?.id}`, {
        method: "PATCH", headers: baseHeaders,
        body: JSON.stringify(args?.req),
      });
      break;
    case "delete_llm_config":
      res = await fetch(`${BACKEND}/api/settings/llm/${args?.id}`, { method: "DELETE" });
      if (res.status === 204) return undefined as T;
      break;
    case "set_default_llm":
      res = await fetch(`${BACKEND}/api/settings/llm/${args?.id}/default`, { method: "PUT" });
      break;

    // ---- Agent Template CRUD ----
    case "list_agent_templates":
      res = await fetch(`${BACKEND}/api/settings/agents`);
      break;
    case "update_agent_template":
      res = await fetch(`${BACKEND}/api/settings/agents/${args?.id}`, {
        method: "PATCH", headers: baseHeaders,
        body: JSON.stringify(args?.req),
      });
      break;

    // ---- Chat ----
    case "send_chat_message":
      res = await fetch(`${BACKEND}/api/inspirations/${args?.inspirationId}/chat`, {
        method: "POST", headers: baseHeaders,
        body: JSON.stringify({ content: args?.content }),
      });
      break;
    case "get_messages": {
      const params = new URLSearchParams();
      if (args?.limit) params.set("limit", String(args.limit));
      if (args?.before) params.set("before", String(args.before));
      res = await fetch(`${BACKEND}/api/inspirations/${args?.inspirationId}/messages?${params}`);
      break;
    }

    default:
      throw new Error(`Unknown command: ${cmd}`);
  }

  if (!res!.ok) {
    const err = await res!.text();
    throw new Error(err || `${cmd} failed (${res!.status})`);
  }
  return res!.json();
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

// ---- Chat ----

export async function sendChatMessage(
  inspirationId: string,
  content: string
): Promise<Message> {
  return call<Message>("send_chat_message", { inspirationId, content });
}

export async function getMessages(
  inspirationId: string,
  limit?: number,
  before?: string | null
): Promise<Message[]> {
  return call<Message[]>("get_messages", {
    inspirationId,
    limit: limit || 50,
    before: before || null,
  });
}
