# tools/ — project tooling

Utilities around the game client and protocol. Nothing here ships to
players; everything here must run without committing game assets.

## Layout (current + planned)

| Path | Status | Purpose |
| --- | --- | --- |
| `client-sourcing/` | **in use** | Obtain clients from official community sources: MEGA listing/downloading (`mega.py ls`/`get`), Google Drive listing (`parse-drive.js`), re-archive into multi-volume 7z (`rearchive-clients.sh`). |
| `branding/` | **in use** | `apply_branding.py apply`: swaps the login-stage "made by" page inside a client `game_pak` with our own (pak-scan + pak-put). Re-run to change the text; apply before re-archiving for distribution. |
| `ui/` | **in use** | Custom Lua UI for the client (info panel on login/server-select). `push-ui.ps1` = compile (Lua 5.1-float toolchain) + inject into game_pak. Full how-to and discoveries in `ui/README.md`. |
| `db/` | **in use** | `dbtext.py`: search/edit the client's localized UI strings (`compact.sqlite3` → `localized_texts`) from the CLI, with manifest hash sync. |
| `pak/` | planned | `game_pak` reader/writer; build delta patches and content packs for the launcher manifests. |
| `opcode/` | planned | Opcode discovery and diffing between client versions (`OpcodeAndNameFinder`-style), tshark dissector configs. |
| `re/` | planned | Reverse-engineering workspace: Ghidra/IDA scripts, Ghidra-MCP notes, packet captures analysis. Targets are **client** binaries/protocol for interoperability — never redistributed here. |
| `editors/` | planned | World/content editors: spawns, zones, items, quests — producing server data or content packs. |
| `converters/` | planned | Data converters between version lines (see also `servers/aaemu/Tools/WorldConverter`). |

## Rules

- Inputs come from local gitignored folders: `.clients/` (archives),
  `.client_files/` (extracted installs) — see `.client_files/README.md`.
- Outputs that reach players go through `content/manifests/` +
  `scripts/upload-client.sh` (S3/HTTP + SHA256).
- Any script that scrapes third-party pages downloads live; never commit
  scraped HTML dumps (secret-scanning false positives, stale data).
