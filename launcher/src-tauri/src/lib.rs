use serde::Serialize;

/// Estado de una instalación de client (scaffold: stub).
#[derive(Serialize)]
struct ClientStatus {
    installed: bool,
    verified: bool,
    files: usize,
}

/// Prepara (descarga/parchea/verifica) el client de una versión.
/// Scaffold: stub — el client manager real (manifiesto + chunks SHA256 +
/// parcheo delta) es el workstream M1.
#[tauri::command]
fn client_status(_version: String) -> ClientStatus {
    ClientStatus {
        installed: false,
        verified: false,
        files: 0,
    }
}

/// Lanza archeage.exe contra el login server de la versión elegida.
/// Scaffold: stub — escribe la config del client (settings.aelcf-equivalente)
/// y arranca el proceso (M1).
#[tauri::command]
fn client_launch(version: String, server_id: String) -> Result<String, String> {
    Ok(format!("launch {version}/{server_id} (stub — M1)"))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![client_status, client_launch])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
