use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

// ---------------------------------------------------------------------------
// Manifest (contract with content/manifests/{v}.json)
// ---------------------------------------------------------------------------

#[derive(Deserialize)]
pub struct Manifest {
    /// Part of the contract; the version is passed as an argument and client is informational.
    #[allow(dead_code)]
    pub version: String,
    #[allow(dead_code)]
    pub client: String,
    pub files: Vec<ManifestFile>,
    pub extract: ExtractConfig,
    pub verify: Vec<VerifyEntry>,
    pub login: LoginManifest,
    #[serde(default)]
    pub patches: Vec<PatchedFile>,
}

#[derive(Deserialize)]
pub struct ManifestFile {
    pub name: String,
    /// "direct" = installed as-is | "archive" = part of a compressed archive
    pub kind: String,
    /// "drive:FILEID" | "https://..."
    pub url: String,
    /// 0 = unknown (the real Content-Length is used)
    #[serde(default)]
    pub size: u64,
    /// "" = unknown (the launcher computes it on the first download and stores it)
    #[serde(default)]
    pub sha256: String,
}

#[derive(Deserialize)]
pub struct ExtractConfig {
    /// Part that 7-Zip uses as input for the spanned archive
    pub archive: String,
    /// Extraction tool (always "7z" for now).
    #[allow(dead_code)]
    #[serde(default)]
    pub tool: String,
}

#[derive(Deserialize)]
pub struct VerifyEntry {
    pub path: String,
    #[serde(rename = "minSize")]
    pub min_size: u64,
}

#[derive(Deserialize)]
pub struct LoginManifest {
    #[serde(default)]
    pub protocol: String,
}

#[derive(Deserialize)]
pub struct PatchedFile {
    pub path: String,
    /// Patch type: "pak" | "lua" | "sqlite" — consumed by the merge (M2).
    #[serde(rename = "type")]
    #[allow(dead_code)]
    pub kind: String,
    pub url: String,
    pub sha256: String,
}

// ---------------------------------------------------------------------------
// Status / progress (exposed to the UI)
// ---------------------------------------------------------------------------

#[derive(Serialize, Clone)]
pub struct InstallStatus {
    pub version: String,
    pub installed: bool,
    pub verified: bool,
    pub files: usize,
    pub install_dir: String,
}

#[derive(Serialize, Clone)]
pub struct Progress {
    /// "download" | "verify" | "extract" | "install" | "done"
    pub stage: String,
    pub file: String,
    pub downloaded: u64,
    pub total: u64,
}

// ---------------------------------------------------------------------------
// Persisted launcher config (install folders, known hashes)
// ---------------------------------------------------------------------------

#[derive(Serialize, Deserialize, Default)]
pub struct LauncherConfig {
    #[serde(default)]
    pub versions: HashMap<String, VersionConfig>,
}

#[derive(Serialize, Deserialize, Default)]
pub struct VersionConfig {
    #[serde(default)]
    pub install_dir: String,
    #[serde(default)]
    pub hashes: HashMap<String, String>,
}

fn app_base_dir() -> PathBuf {
    std::env::var("LOCALAPPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|_| std::env::temp_dir().join("ArcheaAge"))
        .join("ArcheaAge")
}

pub fn config_path() -> PathBuf {
    app_base_dir().join("config.json")
}

pub fn load_config() -> LauncherConfig {
    let path = config_path();
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

fn save_config(cfg: &LauncherConfig) -> Result<(), String> {
    let path = config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    std::fs::write(&path, serde_json::to_string_pretty(cfg).unwrap()).map_err(|e| e.to_string())
}

/// Install folder for a version (user-configurable).
pub fn install_dir(version: &str) -> PathBuf {
    let cfg = load_config();
    cfg.versions
        .get(version)
        .and_then(|v| {
            if v.install_dir.is_empty() {
                None
            } else {
                Some(PathBuf::from(&v.install_dir))
            }
        })
        .unwrap_or_else(|| app_base_dir().join("clients").join(version))
}

pub fn set_install_dir(version: &str, dir: &str) -> Result<(), String> {
    let mut cfg = load_config();
    cfg.versions
        .entry(version.to_string())
        .or_default()
        .install_dir = dir.to_string();
    save_config(&cfg)
}

// ---------------------------------------------------------------------------
// Local install state
// ---------------------------------------------------------------------------

fn file_ok(full: &Path, min_size: u64) -> bool {
    full.exists() && full.metadata().map(|m| m.len()).unwrap_or(0) >= min_size
}

pub fn status(version: &str, manifest: &Manifest) -> InstallStatus {
    let dir = install_dir(version);
    let ok = manifest
        .verify
        .iter()
        .filter(|v| file_ok(&dir.join(&v.path), v.min_size))
        .count();
    let total = manifest.verify.len();
    InstallStatus {
        version: version.to_string(),
        installed: ok > 0,
        verified: total > 0 && ok == total,
        files: ok,
        install_dir: dir.to_string_lossy().into_owned(),
    }
}

// ---------------------------------------------------------------------------
// Download from Google Drive (confirm token + cookies + Range resume)
// ---------------------------------------------------------------------------

fn drive_file_id(url: &str) -> Option<&str> {
    url.strip_prefix("drive:")
}

fn extract_uuid(html: &str) -> Option<String> {
    const MARK: &str = "name=\"uuid\" value=\"";
    let start = html.find(MARK)? + MARK.len();
    let end = html[start..].find('"')? + start;
    Some(html[start..end].to_string())
}

fn is_html(resp: &reqwest::Response) -> bool {
    resp.headers()
        .get(reqwest::header::CONTENT_TYPE)
        .map(|v| v.to_str().unwrap_or("").contains("text/html"))
        .unwrap_or(false)
}

/// Detects a corrupt file: Drive error HTML page instead of the binary.
fn looks_like_html_bytes(buf: &[u8]) -> bool {
    let head = String::from_utf8_lossy(buf).to_lowercase();
    head.contains("<!doctype") || head.contains("<html")
}

fn looks_like_html(path: &Path) -> bool {
    let mut buf = [0u8; 512];
    let n = std::fs::File::open(path)
        .ok()
        .and_then(|mut f| std::io::Read::read(&mut f, &mut buf).ok())
        .unwrap_or(0);
    looks_like_html_bytes(&buf[..n])
}

/// Usable size of a partial file: cleans up corrupt ones (HTML or > expected).
fn usable_existing(dest: &Path, expected: u64) -> u64 {
    if !dest.exists() {
        return 0;
    }
    let len = dest.metadata().map(|m| m.len()).unwrap_or(0);
    if (expected > 0 && len > expected) || looks_like_html(dest) {
        let _ = std::fs::remove_file(dest);
        0
    } else {
        len
    }
}

/// Writes the body of an already-sent response to `dest` with resume and validation.
async fn write_stream(
    resp: reqwest::Response,
    dest: &Path,
    existing: u64,
    expected: u64,
    on_progress: &(dyn Fn(u64, u64) + Send + Sync),
) -> Result<u64, String> {
    use futures_util::StreamExt;
    use tokio::io::AsyncWriteExt;

    if !resp.status().is_success() {
        return Err(format!("HTTP {}", resp.status()));
    }
    let resuming = existing > 0 && resp.status() == reqwest::StatusCode::PARTIAL_CONTENT;
    let mut out = if resuming {
        tokio::fs::OpenOptions::new()
            .append(true)
            .open(dest)
            .await
            .map_err(|e| e.to_string())?
    } else {
        if existing > 0 {
            let _ = std::fs::remove_file(dest);
        }
        tokio::fs::File::create(dest)
            .await
            .map_err(|e| e.to_string())?
    };
    let total = existing + resp.content_length().unwrap_or(expected);
    let mut stream = resp.bytes_stream();
    let mut downloaded: u64 = existing;
    let mut first: Vec<u8> = Vec::new();
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.map_err(|e| e.to_string())?;
        // Early detection: if the server returns error HTML instead of the binary.
        if first.len() < 512 {
            first.extend_from_slice(&chunk[..chunk.len().min(512 - first.len())]);
            if looks_like_html_bytes(&first) && expected > 1024 {
                let _ = std::fs::remove_file(dest);
                return Err("Drive returned HTML instead of the file".to_string());
            }
        }
        out.write_all(&chunk).await.map_err(|e| e.to_string())?;
        downloaded += chunk.len() as u64;
        on_progress(downloaded, total);
    }
    out.flush().await.map_err(|e| e.to_string())?;
    // Size validation: if it doesn't match the expected size, the file is garbage.
    if expected > 0 && downloaded != expected {
        let _ = std::fs::remove_file(dest);
        return Err(format!(
            "size mismatch: expected {expected}, got {downloaded}"
        ));
    }
    Ok(downloaded)
}

/// Downloads a Drive file (id) to `dest` with resume and progress.
async fn drive_download(
    id: &str,
    dest: &Path,
    expected: u64,
    on_progress: &(dyn Fn(u64, u64) + Send + Sync),
) -> Result<(), String> {
    let client = reqwest::Client::builder()
        .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        .build()
        .map_err(|e| e.to_string())?;

    let existing = usable_existing(dest, expected);

    // 1. uc?id=...&export=download → 303 → usercontent → HTML with uuid
    let uc_url = format!("https://drive.google.com/uc?id={id}&export=download");
    let resp = client
        .get(&uc_url)
        .send()
        .await
        .map_err(|e| format!("GET {uc_url}: {e}"))?;

    // Session cookie: reqwest follows the 303 automatically and the Set-Cookie
    // stays in the final response (HTML). We capture it for the 2nd request.
    let session_cookie = resp
        .headers()
        .get_all(reqwest::header::SET_COOKIE)
        .iter()
        .filter_map(|v| v.to_str().ok())
        .map(|c| c.split(';').next().unwrap_or("").to_string())
        .collect::<Vec<_>>()
        .join("; ");

    if is_html(&resp) || resp.status() == reqwest::StatusCode::NOT_FOUND {
        let body = resp.text().await.map_err(|e| e.to_string())?;
        let uuid = extract_uuid(&body)
            .ok_or_else(|| format!("Drive did not return a confirmation token for {id}"))?;
        let dl_url = format!(
            "https://drive.usercontent.google.com/download?id={id}&export=download&confirm=t&uuid={uuid}"
        );
        let mut req = client.get(&dl_url);
        if !session_cookie.is_empty() {
            req = req.header(reqwest::header::COOKIE, &session_cookie);
        }
        // Drive REQUIRES Range to serve large files (without it, it returns HTML).
        req = req.header(reqwest::header::RANGE, format!("bytes={existing}-"));
        let resp = req
            .send()
            .await
            .map_err(|e| format!("GET {dl_url}: {e}"))?;
        if !resp.status().is_success() {
            return Err(format!("GET {dl_url}: HTTP {}", resp.status()));
        }
        write_stream(resp, dest, existing, expected, on_progress).await?;
    } else {
        // Small file without confirmation: direct stream.
        write_stream(resp, dest, existing, expected, on_progress).await?;
    }
    Ok(())
}

/// Download with retries (Drive rate-limits; exponential backoff between attempts).
async fn drive_download_retry(
    id: &str,
    dest: &Path,
    expected: u64,
    on_progress: &(dyn Fn(u64, u64) + Send + Sync),
) -> Result<(), String> {
    let mut last_err = String::new();
    for attempt in 0..8 {
        match drive_download(id, dest, expected, on_progress).await {
            Ok(()) => return Ok(()),
            Err(e) => {
                if attempt < 7 {
                    // Drive blocks by IP for minutes: long backoff.
                    let wait = 60 + attempt * 60;
                    println!("  ↻ retry {}/8 in {wait}s ({e})", attempt + 1);
                    tokio::time::sleep(std::time::Duration::from_secs(wait)).await;
                }
                last_err = e;
            }
        }
    }
    Err(format!("download failed after 8 attempts: {last_err}"))
}

// ---------------------------------------------------------------------------
// SHA256
// ---------------------------------------------------------------------------

pub async fn sha256_of(path: &Path) -> Result<String, String> {
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
    Ok(format!("{:x}", hasher.finalize()))
}

/// Only used by tests (the pipeline uses sha256_of + direct comparison).
#[allow(dead_code)]
async fn verify_sha256(path: &Path, expected: &str) -> Result<(), String> {
    let got = sha256_of(path).await?;
    if got != expected.to_lowercase() {
        return Err(format!(
            "SHA256 mismatch in {}: expected {expected}, got {got}",
            path.display()
        ));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Extraction with 7-Zip
// ---------------------------------------------------------------------------

fn find_7z() -> Option<PathBuf> {
    for cand in ["7z", "7za", "7zz"] {
        if std::process::Command::new(cand)
            .arg("i")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
        {
            return Some(PathBuf::from(cand));
        }
    }
    for dir in [
        "C:\\Program Files\\7-Zip\\7z.exe",
        "C:\\Program Files (x86)\\7-Zip\\7z.exe",
    ] {
        let p = PathBuf::from(dir);
        if p.exists() {
            return Some(p);
        }
    }
    None
}

async fn extract_with_7z(exe: &Path, archive: &Path, dest: &Path) -> Result<(), String> {
    let out = tokio::process::Command::new(exe)
        .arg("x")
        .arg(archive)
        .arg(format!("-o{}", dest.display()))
        .arg("-y")
        .output()
        .await
        .map_err(|e| e.to_string())?;
    if !out.status.success() {
        return Err(format!(
            "7-Zip failed: {}",
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Pipeline: download (temp) → verify → extract → install → clean up → validate
// ---------------------------------------------------------------------------

pub async fn ensure(
    version: &str,
    manifest: &Manifest,
    on_progress: &(dyn Fn(Progress) + Send + Sync),
) -> Result<InstallStatus, String> {
    let dir = install_dir(version);
    let tmp = dir.join(".download");
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&tmp).map_err(|e| e.to_string())?;

    let mut cfg = load_config();
    let known_hashes = cfg.versions.entry(version.to_string()).or_default().hashes.clone();
    let http = reqwest::Client::new();

    let before = status(version, manifest);

    // 1. "direct" files (compact.sqlite3) → temp → verify → move to install dir.
    for f in manifest.files.iter().filter(|f| f.kind == "direct") {
        let target = dir.join(&f.name);
        if file_ok(&target, f.size) {
            continue;
        }
        let dest = tmp.join(&f.name);
        on_progress(            Progress {
                stage: "download".into(),
                file: f.name.clone(),
                downloaded: 0,
                total: f.size,
            },
        );
        if let Some(id) = drive_file_id(&f.url) {
            drive_download_retry(id, &dest, f.size, &|d, t| {
                on_progress(                    Progress {
                        stage: "download".into(),
                        file: f.name.clone(),
                        downloaded: d,
                        total: t,
                    },
                );
            })
            .await?;
        } else {
            return Err(format!("unsupported URL: {}", f.url));
        }

        on_progress(            Progress {
                stage: "verify".into(),
                file: f.name.clone(),
                downloaded: 0,
                total: 0,
            },
        );
        let hash = sha256_of(&dest).await?;
        if !f.sha256.is_empty() && !f.sha256.starts_with("REPLACE_WITH") && hash != f.sha256 {
            return Err(format!("SHA256 mismatch in {}: {}", f.name, hash));
        }
        std::fs::rename(&dest, &target).map_err(|e| e.to_string())?;
        cfg.versions
            .entry(version.to_string())
            .or_default()
            .hashes
            .insert(f.name.clone(), hash);
    }

    // 2. "archive" files (spanned zip parts) → temp → extract with 7-Zip.
    let archives: Vec<&ManifestFile> = manifest
        .files
        .iter()
        .filter(|f| f.kind == "archive")
        .collect();
    if !archives.is_empty() && !before.verified {
        for f in &archives {
            let dest = tmp.join(&f.name);
            let ok = dest.exists()
                && dest.metadata().map(|m| m.len()).unwrap_or(0) == f.size
                && (f.sha256.is_empty()
                    || known_hashes
                        .get(&f.name)
                        .is_some_and(|h| h == &f.sha256));
            if ok {
                continue;
            }
            on_progress(                Progress {
                    stage: "download".into(),
                    file: f.name.clone(),
                    downloaded: 0,
                    total: f.size,
                },
            );
            if let Some(id) = drive_file_id(&f.url) {
                drive_download_retry(id, &dest, f.size, &|d, t| {
                    on_progress(                        Progress {
                            stage: "download".into(),
                            file: f.name.clone(),
                            downloaded: d,
                            total: t,
                        },
                    );
                })
                .await?;
            } else {
                return Err(format!("unsupported URL: {}", f.url));
            }
            // Compute and remember the hash (the manifest does not carry it).
            let hash = sha256_of(&dest).await?;
            cfg.versions
                .entry(version.to_string())
                .or_default()
                .hashes
                .insert(f.name.clone(), hash);
        }

        on_progress(            Progress {
                stage: "extract".into(),
                file: manifest.extract.archive.clone(),
                downloaded: 0,
                total: 0,
            },
        );
        let exe = find_7z().ok_or("7-Zip not found — install 7-Zip (7-zip.org) or add it to the PATH")?;
        extract_with_7z(&exe, &tmp.join(&manifest.extract.archive), &dir).await?;
    }

    // 3. Patches: deltas of our mods (pak/lua/sqlite). Downloaded and verified;
    // the pak-level merge is a separate tool (aapatcher/AAEmu-Packer) — M2.
    for p in &manifest.patches {
        let fname = if p.path.is_empty() {
            p.url.rsplit('/').next().unwrap_or("patch").to_string()
        } else {
            let normalized = p.path.replace('\\', "/");
            normalized.rsplit('/').next().unwrap_or("patch").to_string()
        };
        let full = dir.join("patches").join(&fname);
        if full.exists() && sha256_of(&full).await.map(|h| h == p.sha256).unwrap_or(false) {
            continue; // already downloaded and verified
        }
        if let Some(parent) = full.parent() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        on_progress(            Progress {
                stage: "download".into(),
                file: format!("patch/{fname}"),
                downloaded: 0,
                total: 0,
            },
        );
        if let Some(id) = drive_file_id(&p.url) {
            drive_download_retry(id, &full, 0, &|_d, _t| {}).await?;
        } else {
            let resp = http
                .get(&p.url)
                .send()
                .await
                .map_err(|e| format!("GET {}: {e}", p.url))?;
            if !resp.status().is_success() {
                return Err(format!("GET {}: HTTP {}", p.url, resp.status()));
            }
            let bytes = resp.bytes().await.map_err(|e| e.to_string())?;
            tokio::fs::write(&full, &bytes)
                .await
                .map_err(|e| e.to_string())?;
        }
        if !p.sha256.is_empty() && sha256_of(&full).await? != p.sha256 {
            return Err(format!("SHA256 mismatch in patch {fname}"));
        }
    }

    // 4. Clean up temp files.
    let _ = std::fs::remove_dir_all(&tmp);

    // 4. Validate install.
    save_config(&cfg)?;
    let st = status(version, manifest);
    on_progress(        Progress {
            stage: "done".into(),
            file: String::new(),
            downloaded: if st.verified { 1 } else { 0 },
            total: 1,
        },
    );
    Ok(st)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

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
        assert!(verify_sha256(&p, "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")
            .await
            .is_ok());
        assert!(verify_sha256(&p, "deadbeef").await.is_err());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn drive_id_and_uuid_parsing() {
        assert_eq!(drive_file_id("drive:abc123"), Some("abc123"));
        assert_eq!(drive_file_id("https://x"), None);
        let html = r#"<form action="https://drive.usercontent.google.com/download"><input type="hidden" name="uuid" value="527b795a-5efc-4040-9e1e-6dda68af95af">"#;
        assert_eq!(
            extract_uuid(html).as_deref(),
            Some("527b795a-5efc-4040-9e1e-6dda68af95af")
        );
        assert_eq!(extract_uuid("<html>no token</html>"), None);
    }

    /// Real test against Google Drive: downloads compact.sqlite3 (124 MB) and
    /// verifies its SHA256. Slow and network-dependent — run manually.
    #[tokio::test]
    #[ignore]
    async fn drive_download_compact_sqlite() {
        let dir = std::env::temp_dir().join("archeaage-drive-test");
        std::fs::create_dir_all(&dir).unwrap();
        let dest = dir.join("compact.sqlite3");
        drive_download_retry(
            "18Nm_Q7OgWOfdw_8Xl4TBXa1Z51uGHEIh",
            &dest,
            129_956_864,
            &|d, t| {
                if d % (64 * 1024 * 1024) < 65536 {
                    println!("  {}/{} bytes", d, t);
                }
            },
        )
        .await
        .unwrap();
        let hash = sha256_of(&dest).await.unwrap();
        assert_eq!(
            hash,
            "e580b61b0956c6a664bc8f006f81b243e11a6f7663c6c51b9a4b463f6cd5b0bf"
        );
        let _ = std::fs::remove_dir_all(&dir);
    }
}