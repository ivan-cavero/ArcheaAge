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

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            panel_config_load,
            panel_config_save,
            open_game_documents
        ])
        .run(tauri::generate_context!())
        .expect("error while running UI Studio");
}
