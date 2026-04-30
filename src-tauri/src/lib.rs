use reqwest::Client;
use serde::{Deserialize, Serialize};

const BACKEND_URL: &str = "http://127.0.0.1:8080";

fn http_client() -> Result<Client, String> {
    Client::builder()
        .no_proxy()
        .build()
        .map_err(|e| format!("Failed to build HTTP client: {}", e))
}

fn urlencoding(s: &str) -> String {
    let mut result = String::new();
    for byte in s.bytes() {
        match byte {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                result.push(byte as char);
            }
            b' ' => result.push_str("%20"),
            _ => {
                result.push_str(&format!("%{:02X}", byte));
            }
        }
    }
    result
}

// ---- Types ----

#[derive(Debug, Serialize, Deserialize)]
struct Inspiration {
    id: String,
    name: String,
    #[serde(default)]
    agent_count: i32,
    #[serde(default)]
    latest_message_at: Option<String>,
    created_at: String,
    updated_at: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct LLMConfig {
    id: String,
    provider: String,
    model: String,
    api_key: String,
    base_url: String,
    api_format: String,
    is_default: bool,
    created_at: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct AgentTemplate {
    id: String,
    name: String,
    role: String,
    default_model: String,
    auto_join: bool,
    system_prompt: String,
    created_at: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct Message {
    id: String,
    inspiration_id: String,
    agent_id: Option<String>,
    role: String,
    content: String,
    created_at: String,
    #[serde(default)]
    agent_name: Option<String>,
    #[serde(default)]
    agent_number: Option<i32>,
    #[serde(default)]
    agent_model: Option<String>,
    #[serde(default = "default_chat_mode")]
    mode: String,
    #[serde(default)]
    brainstorm_session_id: Option<String>,
}

fn default_chat_mode() -> String {
    "chat".to_string()
}

// ---- Greet / Echo (Phase 0) ----

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Sloth Agent backend is running.", name)
}

#[tauri::command]
async fn echo(message: String) -> Result<String, String> {
    let client = http_client()?;
    let body = serde_json::json!({ "message": message });
    let resp = client
        .post(format!("{}/api/echo", BACKEND_URL))
        .header("Content-Type", "application/json")
        .body(body.to_string())
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    let body: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("JSON parse error: {}", e))?;
    Ok(body["echo"].as_str().unwrap_or("No echo key").to_string())
}

// ---- Inspiration CRUD (Iter-1) ----

#[tauri::command]
async fn create_inspiration(name: String) -> Result<Inspiration, String> {
    let client = http_client()?;
    let body = serde_json::json!({ "name": name });
    let resp = client
        .post(format!("{}/api/inspirations", BACKEND_URL))
        .header("Content-Type", "application/json")
        .body(body.to_string())
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to create inspiration: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[tauri::command]
async fn list_inspirations(query: Option<String>) -> Result<Vec<Inspiration>, String> {
    let client = http_client()?;
    let mut url = format!("{}/api/inspirations", BACKEND_URL);
    if let Some(q) = &query {
        url = format!("{}?q={}", url, urlencoding(&q));
    }
    let resp = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to list inspirations: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[tauri::command]
async fn get_inspiration(id: String) -> Result<Inspiration, String> {
    let client = http_client()?;
    let resp = client
        .get(format!("{}/api/inspirations/{}", BACKEND_URL, id))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Inspiration not found: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[tauri::command]
async fn delete_inspiration(id: String) -> Result<(), String> {
    let client = http_client()?;
    let resp = client
        .delete(format!("{}/api/inspirations/{}", BACKEND_URL, id))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to delete inspiration: {}", detail));
    }
    Ok(())
}

// ---- LLM Config CRUD (Iter-2) ----

#[tauri::command]
async fn list_llm_configs() -> Result<Vec<LLMConfig>, String> {
    let client = http_client()?;
    let resp = client
        .get(format!("{}/api/settings/llm", BACKEND_URL))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to list LLM configs: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[tauri::command]
async fn create_llm_config(req: LLMCreateRequest) -> Result<LLMConfig, String> {
    let client = http_client()?;
    let body = serde_json::to_string(&req).map_err(|e| e.to_string())?;
    let resp = client
        .post(format!("{}/api/settings/llm", BACKEND_URL))
        .header("Content-Type", "application/json")
        .body(body)
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to create LLM config: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[derive(Debug, Serialize, Deserialize)]
struct LLMCreateRequest {
    provider: String,
    model: String,
    api_key: String,
    base_url: String,
    #[serde(default = "default_api_format")]
    api_format: String,
}

fn default_api_format() -> String {
    "openai".to_string()
}

#[tauri::command]
async fn update_llm_config(id: String, req: LLMUpdateRequest) -> Result<LLMConfig, String> {
    let client = http_client()?;
    let body = serde_json::to_string(&req).map_err(|e| e.to_string())?;
    let resp = client
        .patch(format!("{}/api/settings/llm/{}", BACKEND_URL, id))
        .header("Content-Type", "application/json")
        .body(body)
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to update LLM config: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[derive(Debug, Serialize, Deserialize)]
struct LLMUpdateRequest {
    #[serde(skip_serializing_if = "Option::is_none")]
    provider: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    model: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    api_key: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    base_url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    api_format: Option<String>,
}

#[tauri::command]
async fn delete_llm_config(id: String) -> Result<(), String> {
    let client = http_client()?;
    let resp = client
        .delete(format!("{}/api/settings/llm/{}", BACKEND_URL, id))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to delete LLM config: {}", detail));
    }
    Ok(())
}

#[tauri::command]
async fn set_default_llm(id: String) -> Result<LLMConfig, String> {
    let client = http_client()?;
    let resp = client
        .put(format!("{}/api/settings/llm/{}/default", BACKEND_URL, id))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to set default LLM: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

// ---- Agent Template CRUD (Iter-2) ----

#[tauri::command]
async fn list_agent_templates() -> Result<Vec<AgentTemplate>, String> {
    let client = http_client()?;
    let resp = client
        .get(format!("{}/api/settings/agents", BACKEND_URL))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to list agent templates: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[tauri::command]
async fn update_agent_template(id: String, req: AgentTemplateUpdateRequest) -> Result<AgentTemplate, String> {
    let client = http_client()?;
    let body = serde_json::to_string(&req).map_err(|e| e.to_string())?;
    let resp = client
        .patch(format!("{}/api/settings/agents/{}", BACKEND_URL, id))
        .header("Content-Type", "application/json")
        .body(body)
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to update agent template: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[derive(Debug, Serialize, Deserialize)]
struct AgentTemplateUpdateRequest {
    #[serde(skip_serializing_if = "Option::is_none")]
    name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    default_model: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    system_prompt: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    auto_join: Option<bool>,
}

// ---- Chat (Iter-2) ----

#[tauri::command]
async fn send_chat_message(
    inspiration_id: String,
    content: String,
    mode: Option<String>,
    brainstorm_session_id: Option<String>,
) -> Result<Message, String> {
    let client = http_client()?;
    let body = serde_json::json!({
        "content": content,
        "mode": mode.unwrap_or_else(|| "chat".to_string()),
        "brainstorm_session_id": brainstorm_session_id,
    });
    let resp = client
        .post(format!("{}/api/inspirations/{}/chat", BACKEND_URL, inspiration_id))
        .header("Content-Type", "application/json")
        .body(body.to_string())
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Chat failed: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[tauri::command]
async fn get_messages(
    inspiration_id: String,
    limit: u32,
    before: Option<String>,
    brainstorm_session_id: Option<String>,
) -> Result<Vec<Message>, String> {
    let client = http_client()?;
    let mut url = format!(
        "{}/api/inspirations/{}/messages?limit={}",
        BACKEND_URL, inspiration_id, limit
    );
    if let Some(b) = &before {
        url = format!("{}&before={}", url, b);
    }
    if let Some(sid) = &brainstorm_session_id {
        url = format!("{}&brainstorm_session_id={}", url, sid);
    }
    let resp = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to get messages: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

// ---- Brainstorm Sessions (Iter-4) ----

#[derive(Debug, Serialize, Deserialize)]
struct BrainstormSession {
    id: String,
    inspiration_id: String,
    title: String,
    status: String,
    sandbox_path: String,
    max_messages: i32,
    cooldown_seconds: i32,
    message_count: i32,
    summary: Option<String>,
    started_by: Option<String>,
    notification_sent: bool,
    created_at: String,
    ended_at: Option<String>,
    file_tree: Vec<serde_json::Value>,
}

#[tauri::command]
async fn create_brainstorm_session(inspiration_id: String, title: String) -> Result<BrainstormSession, String> {
    let client = http_client()?;
    let body = serde_json::json!({ "title": title });
    let resp = client
        .post(format!(
            "{}/api/inspirations/{}/brainstorm-sessions",
            BACKEND_URL, inspiration_id
        ))
        .header("Content-Type", "application/json")
        .body(body.to_string())
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to create brainstorm session: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[tauri::command]
async fn list_brainstorm_sessions(inspiration_id: String) -> Result<Vec<BrainstormSession>, String> {
    let client = http_client()?;
    let resp = client
        .get(format!(
            "{}/api/inspirations/{}/brainstorm-sessions",
            BACKEND_URL, inspiration_id
        ))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to list brainstorm sessions: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[tauri::command]
async fn get_brainstorm_session(session_id: String) -> Result<BrainstormSession, String> {
    let client = http_client()?;
    let resp = client
        .get(format!("{}/api/brainstorm-sessions/{}", BACKEND_URL, session_id))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to get brainstorm session: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[tauri::command]
async fn update_brainstorm_session(session_id: String, data: serde_json::Value) -> Result<BrainstormSession, String> {
    let client = http_client()?;
    let resp = client
        .patch(format!("{}/api/brainstorm-sessions/{}", BACKEND_URL, session_id))
        .header("Content-Type", "application/json")
        .body(data.to_string())
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to update brainstorm session: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

// ---- Agent Team Management (Iter-3) ----

#[derive(Debug, Serialize, Deserialize)]
struct TeamAgent {
    id: String,
    inspiration_id: String,
    template_id: Option<String>,
    name: String,
    role: String,
    model: String,
    status: String,
    joined_at: String,
}

#[tauri::command]
async fn list_agents(inspiration_id: String) -> Result<Vec<TeamAgent>, String> {
    let client = http_client()?;
    let resp = client
        .get(format!("{}/api/inspirations/{}/agents", BACKEND_URL, inspiration_id))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to list agents: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[tauri::command]
async fn add_agent_to_team(inspiration_id: String, template_id: String) -> Result<TeamAgent, String> {
    let client = http_client()?;
    let body = serde_json::json!({ "template_id": template_id });
    let resp = client
        .post(format!("{}/api/inspirations/{}/agents", BACKEND_URL, inspiration_id))
        .header("Content-Type", "application/json")
        .body(body.to_string())
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to add agent to team: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[tauri::command]
async fn update_agent(agent_id: String, model: String) -> Result<TeamAgent, String> {
    let client = http_client()?;
    let body = serde_json::json!({ "model": model });
    let resp = client
        .patch(format!("{}/api/agents/{}", BACKEND_URL, agent_id))
        .header("Content-Type", "application/json")
        .body(body.to_string())
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to update agent: {}", detail));
    }
    resp.json().await.map_err(|e| format!("JSON parse error: {}", e))
}

#[tauri::command]
async fn remove_agent_from_team(inspiration_id: String, agent_id: String) -> Result<(), String> {
    let client = http_client()?;
    let resp = client
        .delete(format!(
            "{}/api/inspirations/{}/agents/{}",
            BACKEND_URL, inspiration_id, agent_id
        ))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    if !resp.status().is_success() {
        let detail = resp.text().await.unwrap_or_default();
        return Err(format!("Failed to remove agent from team: {}", detail));
    }
    Ok(())
}

// ---- Entry Point ----

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            echo,
            create_inspiration,
            list_inspirations,
            get_inspiration,
            delete_inspiration,
            list_llm_configs,
            create_llm_config,
            update_llm_config,
            delete_llm_config,
            set_default_llm,
            list_agent_templates,
            update_agent_template,
            list_agents,
            add_agent_to_team,
            update_agent,
            remove_agent_from_team,
            send_chat_message,
            get_messages,
            create_brainstorm_session,
            list_brainstorm_sessions,
            get_brainstorm_session,
            update_brainstorm_session,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Sloth Agent");
}
