export interface ProviderPreset {
  key: string;
  name: string;
  base_url: string;
  models: string[];
  api_format: "openai" | "anthropic";
}

export const PROVIDER_PRESETS: ProviderPreset[] = [
  {
    key: "deepseek",
    name: "DeepSeek",
    base_url: "https://api.deepseek.com/v1",
    models: ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"],
    api_format: "openai",
  },
  {
    key: "qwen",
    name: "Qwen",
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    models: ["qwen3.6-max-preview", "qwen3.6-plus", "qwen3.6-flash", "qwen3-max", "qwen3-coder-next"],
    api_format: "openai",
  },
  {
    key: "kimi",
    name: "Kimi",
    base_url: "https://api.moonshot.cn/v1",
    models: ["kimi-k2.6", "kimi-k2.5", "moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"],
    api_format: "openai",
  },
  {
    key: "glm",
    name: "GLM (Zhipu)",
    base_url: "https://open.bigmodel.cn/api/paas/v4",
    models: ["glm-5.1", "glm-5-turbo", "glm-4.7-flash", "glm-4-plus", "glm-4-flash"],
    api_format: "openai",
  },
  {
    key: "minimax",
    name: "MiniMax",
    base_url: "https://api.minimax.chat/v1",
    models: ["minimax-m2.7", "abab7.0", "abab6.5s-chat"],
    api_format: "openai",
  },
  {
    key: "xiaomimimo",
    name: "Xiaomi Mimo",
    base_url: "https://api.xiaomimimo.com/v1",
    models: ["mimo-chat"],
    api_format: "openai",
  },
];

export const API_FORMATS = [
  { value: "openai", label: "OpenAI Compatible" },
  { value: "anthropic", label: "Anthropic" },
];
