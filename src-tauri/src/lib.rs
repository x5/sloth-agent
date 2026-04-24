use reqwest::Client;
use serde::{Deserialize, Serialize};

const BACKEND_URL: &str = "http://127.0.0.1:8080";

fn http_client() -> Result<Client, String> {
    Client::builder()
        .no_proxy()
        .build()
        .map_err(|e| format!("Failed to build HTTP client: {}", e))
}

#[derive(Debug, Serialize, Deserialize)]
struct Inspiration {
    id: String,
    name: String,
    created_at: String,
    updated_at: String,
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
        ])
        .run(tauri::generate_context!())
        .expect("error while running Sloth Agent");
}
