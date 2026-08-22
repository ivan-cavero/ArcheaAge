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
    /// Optional absolute path this client build hard-requires (e.g. a repacked
    /// client baked with `C:\AAEMU` paths). Empty = disabled: the ticket flow
    /// (which skips the login UI that referenced those paths) works without it.
    #[serde(default)]
    pub requires_path: String,
    #[serde(default)]
    pub patches: Vec<PatchedFile>,
}

#[derive(Clone, Deserialize)]
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

#[derive(Clone, Default, Deserialize)]
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

#[derive(Clone, Default, Deserialize)]
pub struct LoginManifest {
    #[serde(default)]
    pub protocol: String,
    /// Public login server port; defaults to 1237 when absent.
    #[serde(default)]
    pub port: Option<u16>,
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
    /// Saved launcher credentials (password kept only as SHA-256 hex).
    #[serde(default)]
    pub login: Option<LoginCredentials>,
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

pub fn save_config(cfg: &LauncherConfig) -> Result<(), String> {
    let path = config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    std::fs::write(&path, serde_json::to_string_pretty(cfg).unwrap()).map_err(|e| e.to_string())
}

/// Portable default root: the folder the launcher exe lives in, so installs
/// travel with it (`<launcher>/instances/<version>`). Dev runs land in
/// target/debug; override via config.json / the folder picker if needed.
fn default_install_root() -> PathBuf {
    std::env::current_exe()
        .ok()
        .and_then(|e| e.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(app_base_dir)
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
        .unwrap_or_else(|| default_install_root().join("instances").join(version))
}

pub fn set_install_dir(version: &str, dir: &str) -> Result<(), String> {
    let mut cfg = load_config();
    cfg.versions
        .entry(version.to_string())
        .or_default()
        .install_dir = dir.to_string();
    save_config(&cfg)
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct LoginCredentials {
    pub username: String,
    /// Lowercase hex SHA-256 of the password (used by the Trion ticket).
    pub password_hash: String,
    /// Raw password — required by protocols that pass credentials on the
    /// command line (mailru/xlworld). Stored because the user asked the
    /// launcher to remember the session; never sent anywhere else.
    #[serde(default)]
    pub password: String,
}

pub fn login_get() -> Option<LoginCredentials> {
    load_config().login
}

pub fn login_set(username: &str, password: &str) -> Result<LoginCredentials, String> {
    use sha2::{Digest, Sha256};
    if username.trim().is_empty() || password.is_empty() {
        return Err("empty credentials".into());
    }
    let hash: String = Sha256::digest(password.as_bytes())
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect();
    let mut cfg = load_config();
    let creds = LoginCredentials {
        username: username.trim().to_string(),
        password_hash: hash,
        password: password.to_string(),
    };
    cfg.login = Some(creds.clone());
    save_config(&cfg)?;
    Ok(creds)
}

pub fn login_clear() -> Result<(), String> {
    let mut cfg = load_config();
    cfg.login = None;
    save_config(&cfg)
}

/// Some repacked clients ship with absolute paths baked into their packed UI
/// data (e.g. `C:\AAEMU\bin32\kr`). A directory junction at that exact path
/// pointing at the install dir satisfies them without moving any file.
pub fn ensure_required_path(requires_path: &str, install_dir: &Path) -> Result<(), String> {
    let target = Path::new(requires_path);
    if target.is_empty() || target.exists() {
        return Ok(());
    }
    let parent = target
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("C:\\"));
    std::fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    // Junctions need no admin rights (unlike symlinks); mklink /J is the
    // portable way to create one from Rust without extra crates.
    let out = std::process::Command::new("cmd")
        .args(["/c", "mklink", "/J"])
        .arg(target)
        .arg(install_dir)
        .output()
        .map_err(|e| e.to_string())?;
    if !out.status.success() || !target.exists() {
        return Err(format!(
            "failed to create junction {}: {}",
            target.display(),
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Local install state
// ---------------------------------------------------------------------------

/// Size of a file, or the recursive total of a directory.
///
/// Windows reports directories as 0 bytes, so a folder-based verify entry like
/// `game_pak` (a ~8 GB directory) would never pass a `metadata().len()` check.
fn file_size(path: &Path) -> Option<u64> {
    let meta = path.metadata().ok()?;
    if !meta.is_dir() {
        return Some(meta.len());
    }
    let mut total = 0u64;
    let mut stack = vec![path.to_path_buf()];
    while let Some(dir) = stack.pop() {
        for entry in std::fs::read_dir(&dir).ok()?.flatten() {
            let ft = entry.file_type().ok()?;
            let p = entry.path();
            if ft.is_dir() {
                stack.push(p);
            } else {
                total = total.saturating_add(entry.metadata().map(|m| m.len()).unwrap_or(0));
            }
        }
    }
    Some(total)
}

fn file_ok(full: &Path, min_size: u64) -> bool {
    full.exists() && file_size(full).unwrap_or(0) >= min_size
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

/// Recognizes Google Drive error pages (quota, "too many downloads", …) so the
/// user gets a clear message instead of a generic "no confirmation token".
fn drive_error_hint(html: &str) -> Option<&'static str> {
    let lower = html.to_lowercase();
    if lower.contains("too many users have viewed")
        || lower.contains("can't view or download")
        || lower.contains("cannot view or download")
        || lower.contains("download quota")
    {
        return Some(
            "Google Drive quota reached for this file (\"too many users have viewed or \
             downloaded it recently\"). Wait a few hours or use a mirror.",
        );
    }
    if lower.contains("file cannot be downloaded") || lower.contains("access denied") {
        return Some("Google Drive blocked access to this file (not publicly shared?).");
    }
    None
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
    // Bytes that already belong to `dest` before this response is written.
    // Only count them when we actually resume (206); otherwise the response
    // carries the full file and counting `existing` again would double it and
    // trigger a false "size mismatch" below.
    let base = if resuming { existing } else { 0 };
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
    let total = base + resp.content_length().unwrap_or(expected);
    let mut stream = resp.bytes_stream();
    let mut downloaded: u64 = base;
    let mut first: Vec<u8> = Vec::new();
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.map_err(|e| e.to_string())?;
        // Early detection: if the server returns error HTML instead of the binary.
        if first.len() < 512 {
            first.extend_from_slice(&chunk[..chunk.len().min(512 - first.len())]);
            if looks_like_html_bytes(&first) && expected > 1024 {
                let _ = std::fs::remove_file(dest);
                let head = String::from_utf8_lossy(&first);
                let msg = drive_error_hint(&head)
                    .unwrap_or("Drive returned HTML instead of the file");
                return Err(msg.to_string());
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
        if let Some(hint) = drive_error_hint(&body) {
            return Err(format!("{hint} (file {id})"));
        }
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

/// Locates a 7-Zip CLI. The launcher ships its own copy (7z.exe + 7z.dll under
/// the Tauri resources), so end users never need to install 7-Zip. Only when the
/// bundled copy is missing do we fall back to a system installation.
fn find_7z(resource_dir: Option<&Path>) -> Option<PathBuf> {
    // 1. Bundled with the launcher (embedded via `bundle.resources`).
    let mut bundled: Vec<PathBuf> = Vec::new();
    if let Some(dir) = resource_dir {
        bundled.push(dir.join("sevenzip").join("7z.exe"));
        bundled.push(dir.join("7z.exe"));
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            bundled.push(dir.join("sevenzip").join("7z.exe"));
            bundled.push(dir.join("7z.exe"));
        }
    }
    for cand in bundled {
        if cand.is_file() {
            return Some(cand);
        }
    }

    // 2. System installation (PATH or standard locations).
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

/// Some distributions wrap the client in nested archives (e.g. a spanned ZIP
/// that contains a single `.7z`). After the first extraction, extract any
/// remaining archive found at the install root, repeating until none are left.
async fn extract_nested_archives(exe: &Path, dir: &Path) -> Result<(), String> {
    for _ in 0..3 {
        let archives: Vec<PathBuf> = std::fs::read_dir(dir)
            .ok()
            .into_iter()
            .flatten()
            .flatten()
            .map(|e| e.path())
            .filter(|p| {
                if !p.is_file() {
                    return false;
                }
                p.extension()
                    .and_then(|e| e.to_str())
                    .is_some_and(|e| matches!(e.to_ascii_lowercase().as_str(), "7z" | "zip" | "rar"))
            })
            .collect();
        if archives.is_empty() {
            return Ok(());
        }
        for arc in &archives {
            extract_with_7z(exe, arc, dir).await?;
            let _ = std::fs::remove_file(arc);
        }
    }
    Ok(())
}

/// If the archive wrapped the whole client in a single top-level folder
/// (e.g. `AAEmu Client/game_pak`), move its contents up to the install root so
/// the expected paths (`game_pak`, `bin32`) live where the manifest says.
fn normalize_client_root(dir: &Path) {
    if ["game_pak", "bin32"].iter().any(|n| dir.join(n).exists()) {
        return;
    }
    let work = [".download", ".nested"];
    let Some(nested) = std::fs::read_dir(dir)
        .ok()
        .into_iter()
        .flatten()
        .flatten()
        .filter(|e| e.file_type().map(|t| t.is_dir()).unwrap_or(false))
        .map(|e| e.path())
        .find(|p| {
            let name = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
            !work.contains(&name) && ["game_pak", "bin32"].iter().any(|n| p.join(n).exists())
        })
    else {
        return;
    };
    let tmp = dir.join(".nested");
    if std::fs::rename(&nested, &tmp).is_err() {
        return;
    }
    if let Ok(entries) = std::fs::read_dir(&tmp) {
        for e in entries.flatten() {
            let target = dir.join(e.file_name());
            if !target.exists() {
                let _ = std::fs::rename(e.path(), &target);
            }
        }
    }
    let _ = std::fs::remove_dir_all(&tmp);
}

// ---------------------------------------------------------------------------
// Pipeline: download (temp) → verify → extract → install → clean up → validate
// ---------------------------------------------------------------------------

pub async fn ensure(
    version: &str,
    manifest: &Manifest,
    resource_dir: Option<&Path>,
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

    // Fail fast: if the archives must be extracted, 7-Zip is required. Check
    // BEFORE downloading gigabytes so the user can install it first.
    let needs_extract =
        !before.verified && manifest.files.iter().any(|f| f.kind == "archive");
    let exe = if needs_extract {
        Some(find_7z(resource_dir).ok_or(
            "7-Zip extractor not found (the launcher ships its own copy — \
             reinstall the launcher, or install 7-Zip from 7-zip.org)",
        )?)
    } else {
        None
    };

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
        extract_with_7z(exe.as_ref().unwrap(), &tmp.join(&manifest.extract.archive), &dir)
            .await?;
        // Some distributions wrap everything in a second archive (e.g. a
        // spanned ZIP containing a single .7z) — extract it too, recursively.
        extract_nested_archives(exe.as_ref().unwrap(), &dir).await?;
        // Some archives wrap the whole client in a single top-level folder
        // (e.g. "AAEmu Client/"). Move its contents up to the install root.
        normalize_client_root(&dir);
        // Repacked distributions ship runtime junk from the packer's machine —
        // bin32/debug.log references its old install path (e.g. C:\AAEMU).
        let _ = std::fs::remove_file(dir.join("bin32").join("debug.log"));
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
// Integrity check
// ---------------------------------------------------------------------------

#[derive(Serialize, Clone)]
pub struct VerifyReport {
    pub ok: bool,
    pub checked: usize,
    /// Files compared by full SHA-256 (direct downloads carry the hash).
    pub hashed: usize,
    pub failed: Vec<String>,
}

/// Integrity check for an installed version: direct files with a known
/// manifest sha256 are hashed in full; everything else (incl. the ~24 GB
/// game_pak, whose source archives players don't keep) is presence + min-size.
pub fn verify(version: &str, manifest: &Manifest) -> VerifyReport {
    verify_in(&install_dir(version), manifest)
}

/// Same check against an explicit folder (testable; no config lookup).
pub fn verify_in(dir: &Path, manifest: &Manifest) -> VerifyReport {
    use sha2::{Digest, Sha256};
    use std::io::Read;

    let mut failed: Vec<String> = Vec::new();
    let mut checked = 0usize;
    let mut hashed = 0usize;

    for f in &manifest.files {
        let full = dir.join(&f.name);
        if !full.exists() {
            failed.push(format!("{}: missing", f.name));
            checked += 1;
            continue;
        }
        if f.kind == "direct" && !f.sha256.is_empty() && !f.sha256.starts_with("REPLACE_WITH") {
            hashed += 1;
            let hash_ok = std::fs::File::open(&full).map(|mut file| {
                let mut hasher = Sha256::new();
                let mut buf = [0u8; 65536];
                loop {
                    match file.read(&mut buf) {
                        Ok(0) => break,
                        Ok(n) => hasher.update(&buf[..n]),
                        Err(_) => return false,
                    }
                }
                format!("{:x}", hasher.finalize()) == f.sha256
            });
            if !hash_ok.unwrap_or(false) {
                failed.push(format!("{}: sha256 mismatch", f.name));
            }
        } else if !file_ok(&full, f.size) {
            failed.push(format!("{}: truncated", f.name));
        }
        checked += 1;
    }

    // Verify entries cover installed pieces without download entries
    // (game_pak, bin32/…). Skip ones already covered above.
    let seen: std::collections::HashSet<&str> =
        manifest.files.iter().map(|f| f.name.as_str()).collect();
    for v in &manifest.verify {
        if seen.contains(v.path.as_str()) {
            continue;
        }
        if !file_ok(&dir.join(&v.path), v.min_size) {
            failed.push(format!("{}: missing or truncated", v.path));
        }
        checked += 1;
    }

    VerifyReport {
        ok: failed.is_empty(),
        checked,
        hashed,
        failed,
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn verify_hashes_direct_and_flags_missing() {
        use std::fs;

        let dir = std::env::temp_dir().join("archeaage-test-verify");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        // "hello" → known sha256
        fs::write(dir.join("compact.sqlite3"), b"hello").unwrap();

        let manifest = Manifest {
            version: "1.2".into(),
            client: "t".into(),
            files: vec![
                ManifestFile {
                    name: "compact.sqlite3".into(),
                    kind: "direct".into(),
                    url: "drive:x".into(),
                    size: 5,
                    sha256:
                        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824".into(),
                },
                ManifestFile {
                    name: "missing.bin".into(),
                    kind: "direct".into(),
                    url: "drive:y".into(),
                    size: 0,
                    sha256: String::new(),
                },
            ],
            extract: ExtractConfig {
                archive: String::new(),
                tool: String::new(),
            },
            verify: vec![VerifyEntry {
                path: "game_pak".into(),
                min_size: 1,
            }],
            login: LoginManifest::default(),
            requires_path: String::new(),
            patches: Vec::new(),
        };

        let r = verify_in(&dir, &manifest);
        assert!(!r.ok);
        assert_eq!(r.hashed, 1);
        assert_eq!(r.checked, 3);
        assert!(r.failed.iter().any(|f| f.contains("missing.bin")));
        assert!(r.failed.iter().any(|f| f.contains("game_pak")));

        // Fix everything: pak present + no missing file.
        fs::create_dir_all(dir.join("game_pak")).unwrap();
        fs::write(dir.join("game_pak").join("a.pak"), b"x").unwrap();
        let mut ok_manifest_files = manifest.files.clone();
        ok_manifest_files.remove(1);
        let m2 = Manifest {
            files: ok_manifest_files,
            ..manifest
        };
        let r = verify_in(&dir, &m2);
        assert!(r.ok, "failed: {:?}", r.failed);

        let _ = fs::remove_dir_all(&dir);
    }

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

    #[test]
    fn file_size_sums_directories_recursively() {
        let dir = std::env::temp_dir().join("archeaage-test-dirsize");
        std::fs::create_dir_all(dir.join("game_pak")).unwrap();
        std::fs::create_dir_all(dir.join("game_pak").join("sub")).unwrap();
        std::fs::write(dir.join("game_pak").join("a.pak"), vec![0u8; 100]).unwrap();
        std::fs::write(dir.join("game_pak").join("sub").join("b.pak"), vec![0u8; 50]).unwrap();
        std::fs::write(dir.join("top.bin"), vec![0u8; 10]).unwrap();
        // Windows reports a directory as 0 bytes; the recursive total is what
        // the manifest's `game_pak` verify entry relies on.
        assert_eq!(file_size(&dir).unwrap(), 160);
        assert!(file_ok(&dir, 150));
        assert!(!file_ok(&dir, 161));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn drive_error_hint_recognizes_quota() {
        let quota = "<html>Sorry, you can't view or download this file at this time. Too many users \
                     have viewed or downloaded this file recently.</html>";
        assert!(drive_error_hint(quota).is_some());
        assert!(drive_error_hint("<html>Access denied for this account</html>").is_some());
        // The regular confirm page (virus scan warning + uuid form) is NOT an error.
        assert_eq!(
            drive_error_hint(
                r#"<html><title>Google Drive - Virus scan warning</title><input type="hidden" name="uuid" value="527b795a"></html>"#
            ),
            None
        );
    }

    #[test]
    fn normalize_moves_wrapped_client_up() {
        let dir = std::env::temp_dir().join("archeaage-test-normalize");
        let client = dir.join("AAEmu Client");
        std::fs::create_dir_all(client.join("game_pak")).unwrap();
        std::fs::write(client.join("game_pak").join("game0.pak"), b"x").unwrap();
        std::fs::create_dir_all(client.join("bin32")).unwrap();
        std::fs::write(client.join("bin32").join("archeage.exe"), b"x").unwrap();
        std::fs::write(dir.join("compact.sqlite3"), b"sqlite").unwrap();

        normalize_client_root(&dir);

        assert!(dir.join("game_pak").join("game0.pak").exists());
        assert!(dir.join("bin32").join("archeage.exe").exists());
        assert!(dir.join("compact.sqlite3").exists());
        assert!(!dir.join("AAEmu Client").exists());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn find_7z_prefers_bundled_over_system() {
        let dir = std::env::temp_dir().join("archeaage-7z-bundled");
        let bundle = dir.join("sevenzip");
        std::fs::create_dir_all(&bundle).unwrap();
        std::fs::write(bundle.join("7z.exe"), b"MZ").unwrap();
        // The bundled copy (resource dir) must win over the system install.
        assert_eq!(find_7z(Some(&dir)), Some(bundle.join("7z.exe")));
        let _ = std::fs::remove_dir_all(&dir);
    }

    /// Regression: a partial file + a full (200) response used to double-count
    /// the existing bytes, delete the file and fail with "size mismatch".
    #[tokio::test]
    async fn write_stream_full_response_with_partial_file() {
        use tokio::io::{AsyncReadExt, AsyncWriteExt};
        use tokio::net::TcpListener;

        let body: &[u8] = b"hello";
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        tokio::spawn(async move {
            let (mut sock, _) = listener.accept().await.unwrap();
            let mut buf = [0u8; 4096];
            let _ = sock.read(&mut buf).await;
            let head = format!(
                "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nContent-Type: application/octet-stream\r\n\r\n",
                body.len()
            );
            sock.write_all(head.as_bytes()).await.unwrap();
            sock.write_all(body).await.unwrap();
        });

        let dir = std::env::temp_dir().join("archeaage-test-resume");
        std::fs::create_dir_all(&dir).unwrap();
        let dest = dir.join("part.bin");
        std::fs::write(&dest, b"ab").unwrap(); // existing partial of 2 bytes

        let url = format!("http://{addr}/");
        let resp = reqwest::get(&url).await.unwrap();
        let got = write_stream(resp, &dest, 2, 5, &|_, _| {}).await.unwrap();
        assert_eq!(got, 5);
        assert_eq!(std::fs::read(&dest).unwrap(), body); // full file, not "abhello"
        let _ = std::fs::remove_dir_all(&dir);
    }

    /// Full end-to-end pipeline against the real manifest (~8.3 GB): downloads
    /// the direct file + all spanned ZIP parts from Google Drive, verifies,
    /// extracts with the bundled/system 7-Zip and validates the install.
    /// Installs into the real launcher location (%LOCALAPPDATA%\\ArcheaAge). Run manually.
    #[tokio::test]
    #[ignore]
    async fn full_client_ensure_pipeline() {
        let manifest_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap()
            .parent()
            .unwrap()
            .parent()
            .unwrap()
            .join("content/manifests/1.2.json");
        let raw = std::fs::read_to_string(&manifest_path).unwrap();
        let manifest: Manifest = serde_json::from_str(&raw).unwrap();
        let version = manifest.version.clone();

        let st = ensure(&version, &manifest, None, &|p| {
            if p.stage == "download" && p.downloaded % (64 * 1024 * 1024) < 65536 {
                println!("  {}: {}/{} bytes", p.file, p.downloaded, p.total);
            } else if p.stage == "extract" {
                println!("  extracting with 7-Zip…");
            } else if p.stage == "done" {
                println!("  done: verified={}", p.downloaded > 0);
            }
        })
        .await
        .expect("full client pipeline must succeed");
        assert!(st.verified, "client must be fully installed and verified");
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