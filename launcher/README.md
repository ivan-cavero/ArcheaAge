# ArcheaAge Launcher

Multi-version launcher built on **Tauri v2** (Rust + web): version selector → server browser with live online players → client manager (download/patch/verify) → launch `archeage.exe`.

## Status

- **Modern UI**: dark glassmorphism theme, version selector with status pills, server browser with pulsing dots and load bars, per-stage progress bar (download/verify/extract), install folder picker, registry connection indicator.
- **Full pipeline (Rust)**: `client_ensure` = download to temp → verify SHA256 → extract with 7-Zip (spanned zip) → install into the chosen folder → clean up temp files → validate (`game_pak`, `archeage.exe`, `compact.sqlite3`). Downloads from **real Google Drive** (confirm token + cookies + Range resume) — tested with `compact.sqlite3` (124 MB, SHA256 verified).
- **Pending (M2)**: real pak-level patch merge (aapatcher/AAEmu-Packer tool), exact `settings.aelcf` format from the official launcher.

## Dev

```bash
# 1. Registry running (another terminal)
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
