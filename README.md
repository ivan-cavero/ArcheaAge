# ArcheaAge

[![CI](https://github.com/ivan-cavero/ArcheaAge/actions/workflows/ci.yml/badge.svg)](https://github.com/ivan-cavero/ArcheaAge/actions/workflows/ci.yml)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](LICENSE)

Open source private **ArcheAge** platform: a multi-version launcher, a
metaserver, community plugins and custom content — built on the
[AAEmu](https://github.com/AAEmu/AAEmu) emulator (LGPL-3.0) and a clean-room
Go rewrite in progress.

**Why**: the official ArcheAge service was shut down by XLGAMES/Kakao on
**June 27, 2024** — there is no official way to play the original game
anymore. This project exists so the community can keep it alive: see
[docs/LEGAL.md](docs/LEGAL.md) for the full context and legal analysis.

> **Status**: M1 in progress — launcher client-manager works end to end,
> registry ships in C# today and in Go (Slice 0 of ADR-001).
> Docs: `docs/INVESTIGACION.md` (the why), `docs/ARQUITECTURA.md` (the what),
> `docs/SPEC.md` (the technical contract), `docs/VERSIONS.md` (client versions).

## Vision

1. **Launcher** (Tauri): pick a version → see servers with online players → download/patch the client (with our modifications) → play.
2. **Server** open source: AAEmu fork today, Go rewrite tomorrow; flagship version **1.2**, **3.5** line ("golden age") later.
3. **Plugins**: anyone develops and proposes plugins (AzerothCore model) via `ArcheaAge.Sdk`.
4. **Custom content**: modify the original, improve it, add zones and new development (content packs via the launcher).

## Components (what each thing is)

| Component | What it is | Stack |
| --- | --- | --- |
| **Launcher** (`apps/launcher`) | Desktop app players run: picks a version, lists servers with live player counts, downloads/patches/verifies the client and launches `archeage.exe`. | Rust + Tauri + web |
| **Studio** (`apps/studio`) | In-house editor: 3D world viewport (terrain, CGF, NPCs, doodads) plus the UI layout tools. Bakes from `game_pak` via `tools/world`. | Rust + Tauri + three.js |
| **Registry** (`apps/registry`, Go port in `servers/go/registry`) | Metaserver the launcher queries: available versions, per-version server list with live players (heartbeats from game servers), client manifests, news feed. It never speaks the game protocol. | C#/ASP.NET Core → Go |
| **AAEmu fork** (`servers/aaemu`) | The working game+login servers (submodule of our fork). Production during M1–M2; becomes the protocol/data reference once the Go rewrite catches up. | C#/.NET |
| **Go servers** (`servers/go`) | Clean-room rewrite (ADR-001): registry done, login next, then the game network core and world simulation, slice by slice. | Go |
| **SDK** (`sdk`) | Tiny plugin contract (`IAaPlugin`, event bus) so anyone can compile a plugin **without cloning the server**. Published as NuGet `ArcheaAge.Sdk`. | .NET |
| **Plugins** (`plugins/`) | Community catalog; one folder per plugin, CI keeps a compatibility matrix. | .NET |
| **Content** (`content/`) | Per-version client manifests (files, SHA256, chunks), launcher news feed, and content packs (our client-side deltas: zones, UI, QoL). | JSON |
| **Tools** (`tools/`) | Client sourcing (MEGA/Drive listing, re-archive), packing, opcode/RE utilities; world editors land here later. | mixed |
| **DB** (`db/migrations`) | Our own forward-only SQL migrations. AAEmu's schema lives inside the submodule (`servers/aaemu/SQL`). | SQL |

## Structure

```text
apps/
├── registry/  # ASP.NET Core metaserver (today) — Go port lives in servers/go/registry
├── launcher/  # Tauri v2 (Rust + web): version selector + server browser + client manager
└── studio/    # ArcheaAge Editor: 3D world viewport + UI tools
servers/
├── aaemu/     # AAEmu fork — submodule (origin = ivan-cavero/AAEmu, upstream = AAEmu/AAEmu)
└── go/        # Go rewrite (ADR-001): Slice 0 registry done; login/game next
sdk/          # ArcheaAge.Sdk — plugin contract (NuGet, no AAEmu dependency)
plugins/      # Plugin catalog (Example included)
content/      # Client manifests and content packs
tools/
├── pak/       # Python game_pak reader + CLI (scan/extract/grep). Write = tools/pak-put
├── world/     # heightmap/CGF/vegetation parsers + bake_studio.py
├── ui/        # Lua UI pipeline (decompile → edit → push)
└── client-sourcing/
compose.yaml  # dev DB stack (MariaDB + auto-migrations) — podman/docker compose up -d
db/           # our own SQL migrations (aaemu's live in servers/aaemu/SQL)
scripts/      # dev ops (start-dev, stop-dev, upload-client, write-aelcf)
docs/         # Research, architecture, spec, ADRs
```

Local folders that are **never committed** (see `.gitignore`):
`.clients/` holds the downloaded client archives (~158 GB across versions);
`.client_files/` holds an extracted client used locally by the server's
ClientData and by tools — see `.client_files/README.md`.

## Quick start

### Dev stack (MariaDB + Registry + Login + Game)

```bash
bash scripts/start-dev.sh     # stop with scripts/stop-dev.sh
```

### Registry (requires .NET 10)

```bash
dotnet run --project apps/registry
# GET http://localhost:5080/versions
```

### Registry in Go (servers/go — ADR-001 Slice 0)

```bash
cd servers/go
go run ./registry     # GET http://localhost:5080/versions
go test ./...         # unit tests
```

### SDK + plugins

```bash
dotnet build sdk
dotnet build plugins/Example
```

### Launcher (requires Rust + Node)

```bash
cd apps/launcher
npm install
npm run tauri dev
```

### Studio / editor (requires Rust + Node + Python)

```bash
pip install -r tools/requirements.txt
cd apps/studio
npm install
npm run dev
```

World cache (gitignored) is baked from a local `game_pak`:

```bash
python tools/world/bake_studio.py --pak ".client_files/ArcheAge 1.2 (r208022) for AAEmu/game_pak" \
  --world main_world --overview --out apps/studio/ui/cache
```

### Server (AAEmu fork)

```bash
git submodule update --init servers/aaemu   # clones the fork
# follow the official setup skill: servers/aaemu/.agents/skills/aaemu-setup (docs in the submodule)
```

## Contributing

PRs welcome! Read [CONTRIBUTING.md](CONTRIBUTING.md) first — conventional
commits, tests required for plugins, no game assets ever.

## Funding

Infrastructure costs money. The project's posture is **transparent,
cost-covering donations** — never pay-to-win. Any future monetization will
follow the analysis and mitigations in [docs/LEGAL.md](docs/LEGAL.md §3)
and be announced publicly before it exists.

## License

All code in this repository is licensed under the **GNU LGPL-3.0** (see
[`LICENSE`](LICENSE); [`LICENSE.GPL`](LICENSE.GPL) is included as required by
the LGPL). The AAEmu fork in `servers/aaemu` keeps its upstream licensing.

## Disclaimer

- This project is **not affiliated with, endorsed by, or connected to
  XLGAMES** or any of ArcheAge's publishers (Trion/Gamigo/Kakao/Mail.ru/Tencent).
- **ArcheAge**, its client, artwork, music, trademarks and game data remain
  the property of **XLGAMES**. Nothing like that is distributed from this
  repository: players obtain clients from their own sources, and local
  working copies stay in gitignored folders.
- This is a non-profit, educational/preservation effort around server
  emulation and interoperability. Use at your own risk; no warranty (see
  license sections 15–17).
- Read [docs/LEGAL.md](docs/LEGAL.md) for the full legal context: game
  status, risk analysis by activity (playing / coding / operating /
  monetizing) and the project's funding stance.
