#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Sloth Agent backend is running.", name)
}

#[tauri::command]
async fn echo(message: String) -> Result<String, String> {
    let client = reqwest::Client::builder()
        .no_proxy()
        .build()
        .map_err(|e| format!("Client build: {}", e))?;
    let resp = client
        .post("http://127.0.0.1:8080/api/echo")
        .header("Content-Type", "application/json")
        .body(format!(r#"{{"message":"{}"}}"#, message.replace('"', "\\\"")))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;
    let status = resp.status();
    let text = resp.text().await.map_err(|e| format!("Read error: {}", e))?;
    if text.is_empty() {
        return Err(format!("Empty response, status: {}", status));
    }
    let body: serde_json::Value = serde_json::from_str(&text).map_err(|e| format!("JSON error: {} from '{}'", e, &text[..200.min(text.len())]))?;
    Ok(body["echo"].as_str().unwrap_or("No echo key").to_string())
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![greet, echo])
        .run(tauri::generate_context!())
        .expect("error while running Sloth Agent");
}
