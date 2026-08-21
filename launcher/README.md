# ArcheaAge Launcher

Multi-version launcher built on **Tauri v2** (Rust + web): version selector → server browser with live online players → client manager (download/patch/verify) → launch `archeage.exe`.

## Status

- **Modern UI**: game-launcher style (hero with big PLAY, version chips, install-status badge, tabs for Play/Servers/News, news feed, animated aurora background, glassmorphism).
- **Full pipeline (Rust)**: `client_ensure` = download to temp → verify SHA256 → extract with 7-Zip (spanned zip) → install into the chosen folder → normalize the client root → clean up temp files → validate (`game_pak`, `bin32/archeage.exe`, `compact.sqlite3`). Folder-based verify entries are measured recursively. Downloads from **real Google Drive** (confirm token + cookies + Range resume) with clear quota/HTML errors and 7-Zip detection before the download starts. **7-Zip is bundled** (`src-tauri/sevenzip/`) — end users never need to install it.
- **Pending (M2)**: real pak-level patch merge (aapatcher/AAEmu-Packer tool), exact `settings.aelcf` format from the official launcher.

## Dev

```bash
# 1. Registry running (another terminal, port 5080)
dotnet run --project ../registry

# 2. Launcher
npm install
npm run tauri dev
```

## Contract (spec)

- `client_status(version)` → `{ installed, verified, files }`
- `client_launch(version, serverId)` → writes the client config (pathToGame, serverIPAddress → version's Login, loginType) and launches `archeage.exe`
- Local layout: `%LOCALAPPDATA%/ArcheaAge/clients/{version}/`

See `docs/SPEC.md` §3 for the full detail.
