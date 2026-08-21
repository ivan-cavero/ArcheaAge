# tools/ — project tooling

Utilities around the game client and protocol. Nothing here ships to
players; everything here must run without committing game assets.

## Layout (current + planned)

| Path | Status | Purpose |
| --- | --- | --- |
| `client-sourcing/` | **in use** | Obtain clients from official community sources: MEGA folder listing (`mega-ls*.py`), Google Drive listing (`parse-drive.js`), re-archive into multi-volume 7z (`rearchive-clients.sh`). |
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
