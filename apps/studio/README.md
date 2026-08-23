# apps/studio — ArcheaAge UI Studio

Standalone Tauri app: visual editor for the ivanpanel client addon config
(`Documents\ArcheAge\ivanpanel_config.lua`).

## Run (dev)

The Tauri CLI is shared from the launcher's node_modules:

```powershell
cd apps\studio
..\launcher\node_modules\.bin\tauri.cmd dev
```

First run compiles the Rust crate (~2-5 min). Later runs are fast.

## Build installer-less binary

```powershell
..\launcher\node_modules\.bin\tauri.cmd build
# output in src-tauri\target\release\
```

## Notes

- Frontend is static (`ui/`, no bundler). `withGlobalTauri` exposes
  `window.__TAURI__` for invoke.
- Backend commands (`src-tauri/src/lib.rs`):
  - `panel_config_load` / `panel_config_save` — read/write the config next to
    the game client.
  - `open_game_documents` — opens Documents\ArcheAge in Explorer.
- The game reads that same config at startup; changes apply on next launch.
