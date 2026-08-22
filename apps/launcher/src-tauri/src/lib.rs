pub mod auth_ticket;
pub mod client;

use serde::Serialize;
use tauri::{Emitter, Manager};

/// Registry base URL; override with ARCHEAAGE_REGISTRY.
fn registry_url() -> String {
    std::env::var("ARCHEAAGE_REGISTRY").unwrap_or_else(|_| "http://localhost:5080".to_string())
}

async fn fetch_manifest(version: &str) -> Result<(client::Manifest, String), String> {
    let url = format!("{}/versions/{}/manifest", registry_url(), version);
    let resp = reqwest::get(&url)
        .await
        .map_err(|e| format!("GET {url}: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!("GET {url}: HTTP {}", resp.status()));
    }
    let raw = resp.text().await.map_err(|e| format!("read {url}: {e}"))?;
    let m: client::Manifest =
        serde_json::from_str(&raw).map_err(|e| format!("invalid manifest: {e}"))?;
    Ok((m, raw))
}

fn sha256_hex(s: &str) -> String {
    use sha2::{Digest, Sha256};
    let d = Sha256::digest(s.as_bytes());
    d.iter().map(|b| format!("{b:02x}")).collect()
}

#[derive(Serialize)]
struct ClientStatusView {
    installed: bool,
    verified: bool,
    files: usize,
    install_dir: String,
    update_available: bool,
}

fn view(s: &client::InstallStatus, update_available: bool) -> ClientStatusView {
    ClientStatusView {
        installed: s.installed,
        verified: s.verified,
        files: s.files,
        install_dir: s.install_dir.clone(),
        update_available,
    }
}

/// Local client state for a version (installed/verified).
#[tauri::command]
async fn client_status(version: String) -> Result<ClientStatusView, String> {
    let (manifest, raw) = fetch_manifest(&version).await?;
    let current_hash = sha256_hex(&raw);

    let mut cfg = client::load_config();
    let entry = cfg.versions.entry(version.clone()).or_default();
    let stored = entry.manifest_hash.clone();
    let update_available = stored.is_some() && stored.as_deref() != Some(current_hash.as_str());
    if stored.is_none() {
        entry.manifest_hash = Some(current_hash); // baseline on first sight
        client::save_config(&cfg)?;
    }

    Ok(view(&client::status(&version, &manifest), update_available))
}

/// Download (temp) → verify → extract (7-Zip) → install → clean up → validate.
/// Emits `client-progress` (stage: download|verify|extract|done) to the UI.
#[tauri::command]
async fn client_ensure(app: tauri::AppHandle, version: String) -> Result<ClientStatusView, String> {
    let (manifest, raw) = fetch_manifest(&version).await?;
    // Directory where the bundled 7-Zip lives (embedded via bundle.resources).
    let resource_dir = app.path().resource_dir().ok();
    let st = client::ensure(&version, &manifest, resource_dir.as_deref(), &|p| {
        let _ = app.emit("client-progress", p);
    })
    .await?;
    client::ensure_required_path(
        &manifest.requires_path,
        std::path::Path::new(&st.install_dir),
    )?;

    // Mark this manifest as applied so the Update flag clears.
    let mut cfg = client::load_config();
    cfg.versions
        .entry(version.clone())
        .or_default()
        .manifest_hash = Some(sha256_hex(&raw));
    client::save_config(&cfg)?;

    Ok(view(&st, false))
}

/// Changes the install folder for a version.
#[tauri::command]
async fn client_set_install_dir(version: String, dir: String) -> Result<ClientStatusView, String> {
    client::set_install_dir(&version, &dir)?;
    let (manifest, _raw) = fetch_manifest(&version).await?;
    client::ensure_required_path(&manifest.requires_path, std::path::Path::new(&dir))?;
    Ok(view(
        &client::status(&version, &manifest),
        false, // just re-linked; update flag recomputed on next status
    ))
}

/// Launch configuration per login protocol (see docs/VERSIONS.md).
/// Mirrors the official AAEmu-Launcher per-client launch arguments.
struct LaunchConfig {
    /// executable path relative to the install dir
    exe: &'static str,
    /// argument template — `{ip}`, `{port}`, `{user}`, `{pass}` get substituted
    args: &'static str,
}

fn launch_config(login_type: &str) -> Option<LaunchConfig> {
    let cfg = match login_type {
        "trino_1_2" | "trino_3_5" => LaunchConfig {
            exe: "bin32/archeage.exe",
            // -handle (auth ticket) is appended dynamically at launch time.
            // -lang en_us is REQUIRED: without it the client falls back to the
            // kr locale and pops "Failed to load commands!" at startup.
            args: "-t +auth_ip {ip} -auth_port {port} -lang en_us",
        },
        "trino_6_0" => LaunchConfig {
            exe: "bin64/archeage.exe",
            args: "-t +auth {ip} -auth_port {port} -handle 00000000:00000000 -lang en_us -time_offset 300",
        },
        "trino_7_0" => LaunchConfig {
            exe: "launch_game.exe",
            args: "-eac_launcher_settings settings_32.json -t +auth_ip {ip} -auth_port {port} -handle 00000000:00000000 -lang en_us",
        },
        "kakao_8_0" => LaunchConfig {
            exe: "bin64/archeage.exe",
            args: "-t +auth_ip {ip} -auth_port {port} -authtoken {pass}",
        },
        "mailru_1_0" => LaunchConfig {
            exe: "bin32/archeage.exe",
            args: "-r +auth_ip {ip}:{port} -uid {user} -token {pass}",
        },
        "xlworld_1_0" => LaunchConfig {
            exe: "bin64/archeage.exe",
            args: "-k {pass}",
        },
        _ => return None,
    };
    Some(cfg)
}

/// Launches the game client of the chosen version directly — no third-party
/// launcher involved. Uses the per-protocol arguments from `launch_config`.
#[tauri::command]
async fn client_launch(version: String, server_id: String) -> Result<String, String> {
    use std::process::Command;

    // 1. host of the chosen server (from the registry)
    let servers_url = format!("{}/versions/{}/servers", registry_url(), version);
    let resp = reqwest::get(&servers_url)
        .await
        .map_err(|e| format!("GET {servers_url}: {e}"))?;
    let body: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
    let servers = body["servers"].as_array().ok_or("invalid servers response")?;
    // Empty selection = first available server (the common single-server case).
    let server = servers
        .iter()
        .find(|s| s["id"] == server_id)
        .or_else(|| servers.first())
        .ok_or_else(|| format!("no servers registered for version {version}"))?;
    let host = server["host"].as_str().unwrap_or("127.0.0.1").to_string();

    // 2. launch config based on the manifest's login protocol
    let (manifest, _raw) = fetch_manifest(&version).await?;
    let cfg = launch_config(&manifest.login.protocol)
        .ok_or_else(|| format!("loginType '{}' launch not supported", manifest.login.protocol))?;
    let login_port = manifest.login.port.unwrap_or(1237);

    let dir = client::install_dir(&version);
    let exe = dir.join(cfg.exe);
    if !exe.exists() {
        return Err(format!(
            "client not installed in {} — run client_ensure first",
            exe.display()
        ));
    }

    // 3. substitute per-protocol placeholders using saved credentials
    let creds = client::login_get().ok_or("Not logged in — press Log In first")?;
    let mut args_str = cfg
        .args
        .replace("{ip}", &host)
        .replace("{port}", &login_port.to_string())
        .replace("{user}", &creds.username)
        .replace("{pass}", &creds.password);

    // Trion 1.2/3.5: publish an auth ticket so the client skips its own
    // (flaky) login screen — mirrors the official AAEmu-Launcher flow.
    if matches!(manifest.login.protocol.as_str(), "trino_1_2" | "trino_3_5") {
        args_str += &match auth_ticket::create_trino_ticket_hashed(
            &creds.username,
            &creds.password_hash,
        ) {
            Ok((hmap, hevt)) => format!(" -handle {:08X}:{:08X}", hmap, hevt),
            Err(e) => {
                eprintln!("auth ticket failed, falling back to manual login: {e}");
                " -handle 00000000:00000000".to_string()
            }
        };
    }

    let args: Vec<&str> = args_str.split_whitespace().collect();

    // 4. repacked clients ship baked-in absolute paths (e.g. C:\AAEMU)
    client::ensure_required_path(&manifest.requires_path, &dir)?;

    let bin_dir = exe.parent().map(|p| p.to_path_buf()).unwrap_or(dir);
    let _child = Command::new(&exe)
        .current_dir(&bin_dir)
        .args(&args)
        .spawn()
        .map_err(|e| format!("failed to launch {}: {e}", exe.display()))?;
    Ok(format!(
        "{} launched ({version}/{server_id}) · login {host}:{login_port} · {}",
        cfg.exe, manifest.login.protocol
    ))
}

/// Saved session (username shown in the title bar chip).
#[derive(Serialize)]
struct AuthView {
    username: String,
}

#[tauri::command]
async fn auth_login(username: String, password: String) -> Result<AuthView, String> {
    client::login_set(&username, &password).map(|c| AuthView {
        username: c.username,
    })
}

#[tauri::command]
async fn auth_status() -> Result<Option<AuthView>, String> {
    Ok(client::login_get().map(|c| AuthView {
        username: c.username,
    }))
}

#[tauri::command]
async fn auth_logout() -> Result<(), String> {
    client::login_clear()
}

/// Opens the install folder of a version in Windows Explorer.
#[tauri::command]
async fn open_install_dir(version: String) -> Result<String, String> {    let dir = client::install_dir(&version);
    if !dir.exists() {
        return Err(format!("not installed in {}", dir.display()));
    }
    std::process::Command::new("explorer.exe")
        .arg(&dir)
        .spawn()
        .map_err(|e| format!("no se pudo abrir {}: {e}", dir.display()))?;
    Ok(dir.to_string_lossy().into_owned())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            client_status,
            client_ensure,
            client_set_install_dir,
            client_launch,
            open_install_dir,
            auth_login,
            auth_status,
            auth_logout
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}