use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use tauri::Emitter;

// --- Modelo del manifiesto (contrato con content/manifests/{v}.json) ---

// version/client/patches: parte del contrato; patches se aplican en M2.
#[allow(dead_code)]
#[derive(Deserialize)]
pub struct Manifest {
    pub version: String,
    pub client: String,
    #[serde(default)]
    pub base: BaseManifest,
    #[serde(default)]
    pub patches: Vec<PatchedFile>,
    pub login: LoginManifest,
}

#[derive(Deserialize, Default)]
pub struct BaseManifest {
    #[serde(default)]
    pub source: String,
    #[serde(default)]
    pub files: Vec<ManifestFile>,
}

#[derive(Deserialize)]
pub struct ManifestFile {
    pub path: String,
    #[serde(default)]
    pub size: u64,
    #[serde(default)]
    pub sha256: String,
}

// Aplicación de patches (pak/lua/sqlite) en M2.
#[allow(dead_code)]
#[derive(Deserialize)]
pub struct PatchedFile {
    pub path: String,
    #[serde(rename = "type")]
    pub kind: String,
    pub url: String,
    pub sha256: String,
}

#[derive(Deserialize)]
pub struct LoginManifest {
    #[serde(default)]
    pub protocol: String,
}

// --- Estado / progreso (expuestos a la UI) ---

#[derive(Serialize, Clone)]
pub struct InstallStatus {
    pub version: String,
    pub installed: bool,
    pub verified: bool,
    pub files: usize,
}

#[derive(Serialize, Clone)]
pub struct Progress {
    pub file: String,
    pub downloaded: u64,
    pub total: u64,
}

// --- Layout local ---

pub fn install_dir(version: &str) -> PathBuf {
    let base = std::env::var("LOCALAPPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|_| std::env::temp_dir().join("ArcheaAge"));
    base.join("ArcheaAge").join("clients").join(version)
}

fn file_ok(full: &Path, size: u64) -> bool {
    full.exists() && (size == 0 || full.metadata().map(|m| m.len()).unwrap_or(0) == size)
}

/// Estado local de la instalación: verificado = todos los archivos base con tamaño correcto.
/// ponytail: verificación por tamaño (hash completo es caro en multi-GB); el hash
/// SHA256 se comprueba tras cada descarga y a demanda.
pub fn status(version: &str, manifest: &Manifest) -> InstallStatus {
    let dir = install_dir(version);
    let ok = manifest
        .base
        .files
        .iter()
        .filter(|f| file_ok(&dir.join(&f.path), f.size))
        .count();
    let total = manifest.base.files.len();
    InstallStatus {
        version: version.to_string(),
        installed: ok > 0,
        verified: total > 0 && ok == total,
        files: ok,
    }
}

/// Descarga/parchea/verifica el client de una versión según el manifiesto.
/// Emite eventos `client-progress` a la UI.
pub async fn ensure(app: &tauri::AppHandle, version: &str, manifest: &Manifest) -> Result<(), String> {
    use futures_util::StreamExt;
    use tokio::io::AsyncWriteExt;

    let dir = install_dir(version);
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;

    let http = reqwest::Client::new();
    for f in &manifest.base.files {
        let full = dir.join(&f.path);
        if file_ok(&full, f.size) {
            continue; // ya descargado
        }
        if let Some(parent) = full.parent() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }

        let url = format!(
            "{}/{}",
            manifest.base.source.trim_end_matches('/'),
            f.path.replace('\\', "/")
        );
        let resp = http
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("GET {url}: {e}"))?;
        if !resp.status().is_success() {
            return Err(format!("GET {url}: HTTP {}", resp.status()));
        }
        let total = resp.content_length().unwrap_or(f.size);
        let mut stream = resp.bytes_stream();
        let mut out = tokio::fs::File::create(&full)
            .await
            .map_err(|e| e.to_string())?;
        let mut downloaded: u64 = 0;
        while let Some(chunk) = stream.next().await {
            let chunk = chunk.map_err(|e| e.to_string())?;
            out.write_all(&chunk).await.map_err(|e| e.to_string())?;
            downloaded += chunk.len() as u64;
            let _ = app.emit(
                "client-progress",
                Progress {
                    file: f.path.clone(),
                    downloaded,
                    total,
                },
            );
        }
        out.flush().await.map_err(|e| e.to_string())?;

        if !f.sha256.is_empty() && !f.sha256.starts_with("REPLACE_WITH") {
            verify_sha256(&full, &f.sha256).await?;
        }
    }
    Ok(())
}

async fn verify_sha256(path: &Path, expected: &str) -> Result<(), String> {
    use sha2::{Digest, Sha256};
    use tokio::io::AsyncReadExt;

    let mut f = tokio::fs::File::open(path)
        .await
        .map_err(|e| e.to_string())?;
    let mut hasher = Sha256::new();
    let mut buf = [0u8; 65536];
    loop {
        let n = f.read(&mut buf).await.map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    let got = format!("{:x}", hasher.finalize());
    if got != expected.to_lowercase() {
        return Err(format!(
            "SHA256 mismatch en {}: esperado {expected}, got {got}",
            path.display()
        ));
    }
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn file_ok_checks_size() {
        let dir = std::env::temp_dir().join("archeaage-test");
        std::fs::create_dir_all(&dir).unwrap();
        let p = dir.join("a.bin");
        std::fs::write(&p, b"hello").unwrap();
        assert!(file_ok(&p, 5));
        assert!(!file_ok(&p, 6));
        assert!(!file_ok(&dir.join("missing"), 0));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[tokio::test]
    async fn sha256_verifies_and_rejects() {
        let dir = std::env::temp_dir().join("archeaage-test2");
        std::fs::create_dir_all(&dir).unwrap();
        let p = dir.join("a.bin");
        std::fs::write(&p, b"hello").unwrap();
        // sha256("hello") = 2cf24db...
        assert!(verify_sha256(&p, "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")
            .await
            .is_ok());
        assert!(verify_sha256(&p, "deadbeef").await.is_err());
        let _ = std::fs::remove_dir_all(&dir);
    }
}
