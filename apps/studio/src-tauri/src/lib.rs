//! ArcheaAge Editor — world viewport and UI tools.

use std::path::PathBuf;

/// Repo root: `ARCHEAAGE_ROOT` if set, otherwise walk up from cwd / exe
/// looking for `tools/ui`.
fn repo_root() -> Option<PathBuf> {
    if let Ok(raw) = std::env::var("ARCHEAAGE_ROOT") {
        let p = PathBuf::from(raw);
        if p.join("tools").join("ui").is_dir() {
            return Some(p);
        }
    }
    let mut seeds: Vec<PathBuf> = Vec::new();
    if let Ok(cwd) = std::env::current_dir() {
        seeds.push(cwd);
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            seeds.push(dir.to_path_buf());
        }
    }
    for seed in seeds {
        let mut dir = seed;
        for _ in 0..8 {
            if dir.join("tools").join("ui").is_dir() {
                return Some(dir);
            }
            if !dir.pop() {
                break;
            }
        }
    }
    None
}

fn panel_config_path() -> PathBuf {
    let home = std::env::var("USERPROFILE").unwrap_or_else(|_| ".".into());
    PathBuf::from(home)
        .join("Documents")
        .join("ArcheAge")
        .join("aa_ui_config.lua")
}

/// Reads Documents\ArcheAge\aa_ui_config.lua (None if not created yet).
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
/// push-ui.ps1 picks them up.
#[tauri::command]
async fn overrides_save(content: String) -> Result<String, String> {
    let root = repo_root().ok_or_else(|| {
        "no tools/ui directory found. Set ARCHEAAGE_ROOT to the repo root, \
         or save the file manually into tools\\ui\\overrides.lua"
            .to_string()
    })?;
    let path = root.join("tools").join("ui").join("overrides.lua");
    std::fs::write(&path, content).map_err(|e| format!("{}: {e}", path.display()))?;
    Ok(path.to_string_lossy().into_owned())
}

/// Opens the decompiled Lua source folder of a loginstage module in Explorer.
#[tauri::command]
async fn open_decompiled_source(module: String) -> Result<String, String> {
    let root = repo_root().ok_or_else(|| {
        "decompiled sources not found — run tools\\ui\\decompile.py first \
         (or set ARCHEAAGE_ROOT)"
            .to_string()
    })?;
    let target = root
        .join("tools")
        .join("ui")
        .join("decompiled")
        .join("game/scriptsbin/x2ui/loginstage")
        .join(&module);
    if !target.exists() {
        return Err("decompiled sources not found — run tools\\ui\\decompile.py first".into());
    }
    std::process::Command::new("explorer.exe")
        .arg("/select,")
        .arg(target.clone().into_os_string())
        .spawn()
        .map_err(|e| e.to_string())?;
    Ok(target.to_string_lossy().into_owned())
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            panel_config_load,
            panel_config_save,
            open_game_documents,
            overrides_save,
            open_decompiled_source,
        ])
        .run(tauri::generate_context!())
        .expect("error while running ArcheaAge Editor");
}
