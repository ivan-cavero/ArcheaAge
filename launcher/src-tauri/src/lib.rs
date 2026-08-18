mod client;

use serde::Serialize;

/// Registry base URL: override con ARCHEAAGE_REGISTRY.
fn registry_url() -> String {
    std::env::var("ARCHEAAGE_REGISTRY").unwrap_or_else(|_| "http://localhost:5080".to_string())
}

async fn fetch_manifest(version: &str) -> Result<client::Manifest, String> {
    let url = format!("{}/versions/{}/manifest", registry_url(), version);
    let resp = reqwest::get(&url)
        .await
        .map_err(|e| format!("GET {url}: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!("GET {url}: HTTP {}", resp.status()));
    }
    resp.json::<client::Manifest>()
        .await
        .map_err(|e| format!("manifest inválido: {e}"))
}

#[derive(Serialize)]
struct ClientStatusView {
    installed: bool,
    verified: bool,
    files: usize,
}

fn view(s: &client::InstallStatus) -> ClientStatusView {
    ClientStatusView {
        installed: s.installed,
        verified: s.verified,
        files: s.files,
    }
}

/// Estado local del client de una versión (instalado/verificado).
#[tauri::command]
async fn client_status(version: String) -> Result<ClientStatusView, String> {
    let manifest = fetch_manifest(&version).await?;
    Ok(view(&client::status(&version, &manifest)))
}

/// Descarga/parchea/verifica el client (base → patches) según el manifiesto.
/// Emite `client-progress` a la UI.
#[tauri::command]
async fn client_ensure(app: tauri::AppHandle, version: String) -> Result<ClientStatusView, String> {
    let manifest = fetch_manifest(&version).await?;
    client::ensure(&app, &version, &manifest).await?;
    Ok(view(&client::status(&version, &manifest)))
}

/// Lanza archeage.exe contra el login server de la versión elegida.
/// Escribe la config del client en el install dir y arranca el proceso.
#[tauri::command]
async fn client_launch(version: String, server_id: String) -> Result<String, String> {
    use std::process::Command;

    // 1. host del server elegido (desde el registry)
    let servers_url = format!("{}/versions/{}/servers", registry_url(), version);
    let resp = reqwest::get(&servers_url)
        .await
        .map_err(|e| format!("GET {servers_url}: {e}"))?;
    let body: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
    let server = body["servers"]
        .as_array()
        .and_then(|arr| arr.iter().find(|s| s["id"] == server_id))
        .ok_or_else(|| format!("server {server_id} no encontrado en version {version}"))?;
    let host = server["host"].as_str().unwrap_or("127.0.0.1").to_string();

    // 2. config del client (equivalente a settings.aelcf del launcher oficial)
    let manifest = fetch_manifest(&version).await?;
    let dir = client::install_dir(&version);
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let patches: Vec<String> = manifest.patches.iter().map(|p| p.url.clone()).collect();
    let cfg = serde_json::json!({
        "version": version,
        "serverId": server_id,
        "pathToGame": dir.join("bin32").join("archeage.exe").to_string_lossy(),
        "serverIPAddress": host,
        "loginType": manifest.login.protocol,
        "patches": patches,
    });
    std::fs::write(dir.join("archeaage.config.json"), serde_json::to_string_pretty(&cfg).unwrap())
        .map_err(|e| e.to_string())?;

    // 3. lanzar el client (si está instalado)
    let exe = dir.join("bin32").join("archeage.exe");
    if !exe.exists() {
        return Err(format!(
            "client no instalado en {} — ejecuta client_ensure primero",
            dir.display()
        ));
    }
    let _child = Command::new(&exe)
        .spawn()
        .map_err(|e| format!("no se pudo lanzar {}: {e}", exe.display()))?;
    Ok(format!("archeage.exe lanzado ({version}/{server_id})"))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            client_status,
            client_ensure,
            client_launch
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}