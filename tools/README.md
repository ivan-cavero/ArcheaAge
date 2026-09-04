# tools/ — project tooling

Utilities around the game client and protocol. Nothing here ships to
players; everything here must run without committing game assets.

## Layout (current + planned)

| Path | Status | Purpose |
| --- | --- | --- |
| `client-sourcing/` | **in use** | Obtain clients from official community sources: MEGA listing/downloading (`mega.py ls`/`get`), Google Drive listing (`parse-drive.js`), re-archive into multi-volume 7z (`rearchive-clients.sh`). |
| `branding/` | **in use** | `apply_branding.py apply`: swaps the login-stage "made by" page inside a client `game_pak` with our own (Python extract + `pak-put`). Re-run to change the text; apply before re-archiving for distribution. |
| `ui/` | **in use** | Custom Lua UI for the client (info panel on login/server-select). `push.py` = compile (Lua 5.1-float toolchain) + inject into game_pak. Full how-to and discoveries in `ui/README.md`. |
| `db/` | **in use** | `dbtext.py`: search/edit the client's localized UI strings (`compact.sqlite3` → `localized_texts`) from the CLI, with manifest hash sync. |
| `pak/` | **in use** | Read-only Python `game_pak` library + CLI (`python -m tools.pak scan\|extract\|grep`). Write/replace is still C# (`tools/pak-put`). |
| `world/` | **in use** | Heightmap / CGF / vegetation / NPC parsers and `bake_studio.py` → `apps/studio/ui/cache`. |
| `pak-put/` | **in use** | C# writer (in-place replace + MD5 verify). Keep until Python write exists. |
| `opcode/` | planned | Opcode discovery and diffing between client versions (`OpcodeAndNameFinder`-style), tshark dissector configs. |
| `re/` | planned | Reverse-engineering workspace: Ghidra/IDA scripts, Ghidra-MCP notes, packet captures analysis. Targets are **client** binaries/protocol for interoperability — never redistributed here. |
| `converters/` | planned | Data converters between version lines (see also `servers/aaemu/Tools/WorldConverter`). |

The editor lives in `apps/studio`, not under `tools/`. World bakers here feed it.

Python deps: `pip install -r tools/requirements.txt`.

## Rules

- Inputs come from local gitignored folders: `.clients/` (archives),
  `.client_files/` (extracted installs) — see `.client_files/README.md`.
- Outputs that reach players go through `content/manifests/` +
  `scripts/upload-client.sh` (S3/HTTP + SHA256).
- Any script that scrapes third-party pages downloads live; never commit
  scraped HTML dumps (secret-scanning false positives, stale data).
