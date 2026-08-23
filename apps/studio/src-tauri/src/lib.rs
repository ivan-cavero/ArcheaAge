//! ArcheaAge UI Studio — visual editor for the ivanpanel client addon config.

use std::path::PathBuf;

fn panel_config_path() -> PathBuf {
    let home = std::env::var("USERPROFILE").unwrap_or_else(|_| ".".into());
    PathBuf::from(home)
        .join("Documents")
        .join("ArcheAge")
        .join("ivanpanel_config.lua")
}

/// Reads Documents\ArcheAge\ivanpanel_config.lua (None if not created yet).
#[tauri::command]
async fn panel_config_load() -> Result<Option<String>, String> {
    match std::fs::read_to_string(panel_config_path()) {
        Ok(s) => Ok(Some(s)),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(e.to_string()),
    }
}

/// Writes the config next to the game client.
#[tauri::command]
async fn panel_config_save(content: String) -> Result<String, String> {
    let p = panel_config_path();
    if let Some(dir) = p.parent() {
        std::fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    }
    std::fs::write(&p, content).map_err(|e| e.to_string())?;
    Ok(p.to_string_lossy().into_owned())
}

/// Opens Documents\ArcheAge in Explorer (quick access to config + dumps).
#[tauri::command]
async fn open_game_documents() -> Result<String, String> {
    let dir = panel_config_path()
        .parent()
        .map(|p| p.to_path_buf())
        .unwrap_or_default();
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    std::process::Command::new("explorer.exe")
        .arg(&dir)
        .spawn()
        .map_err(|e| e.to_string())?;
    Ok(dir.to_string_lossy().into_owned())
}

/// Saves generated native-window overrides into tools/ui/overrides.lua so
/// push-ui.ps1 picks them up. Resolves the repo layout relative to cwd/exe.
#[tauri::command]
async fn overrides_save(content: String) -> Result<String, String> {
    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Ok(cwd) = std::env::current_dir() {
        candidates.push(cwd.join("../tools/ui/overrides.lua"));
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            // dev: apps/studio/src-tauri/target/debug -> repo root is 4 up
            let mut p = dir.to_path_buf();
            for _ in 0..4 { p = p.parent().map(|x| x.to_path_buf()).unwrap_or(p); }
            candidates.push(p.join("tools/ui/overrides.lua"));
            // installed: exe beside repo root
            if let Some(parent) = dir.parent() {
                candidates.push(parent.join("tools/ui/overrides.lua"));
            }
        }
    }
    let mut errors = String::new();
    for c in &candidates {
        let Some(parent) = c.parent() else { continue };
        if !parent.exists() { continue; }
        return match std::fs::write(c, content.clone()) {
            Ok(_) => Ok(c.to_string_lossy().into_owned()),
            Err(e) => { errors.push_str(&format!("{}: {e}\n", c.display())); Err(errors) }
        };
    }
    Err(format!("no tools/ui directory found near the app. Tried:\n{errors}\
        \nFallback: save the file manually into tools\\ui\\overrides.lua"))
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            panel_config_load,
            panel_config_save,
            open_game_documents,
            overrides_save
        ])
        .run(tauri::generate_context!())
        .expect("error while running UI Studio");
}
