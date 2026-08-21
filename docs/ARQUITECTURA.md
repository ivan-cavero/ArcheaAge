# Architecture — "ArcheaAge": multi-version launcher + AAEmu fork + plugins

> Complements INVESTIGACION.md. This document is the technical design of the whole system.
> Open decisions are marked **[DECISION]** (see the questions at the end).

---

## 1. System vision (what the user wants)

1. **Launcher**: you open it, pick a **version** (1.2, 3.0...), see the **server list** for that version with **live online players**, join → the launcher **downloads/patches the required client** (with our modifications) → you play.
2. **Open source server**: AAEmu fork (LGPLv3), multi-version across branch lines.
3. **Plugins**: anyone can develop and propose plugins (AzerothCore model).
4. **Custom content**: modify the original, improve it, add zones and new development.

---

## 2. System pieces

```text
┌────────────────────────────────────────────────────────────────────┐
│                        LAUNCHER (client)                          │
│  Version selector │ Server browser (online players) │ Client      │
│  manager (download/patch/verify) │ Launches archeage.exe          │
└───────────────┬──────────────────────────────────┬─────────────────┘
                │ HTTPS (REST API)                 │ writes client config
                ▼                                  ▼
┌───────────────────────────┐          ┌──────────────────────────────┐
│  REGISTRY / METASERVER    │          │  CLIENT INSTALLS (per version)│
│  · available versions     │          │  clients/1.2/  (game_pak,     │
│  · servers per version    │          │    bin32, compact.sqlite3)    │
│  · player counts (live)   │          │  clients/3.0/  ...            │
│  · client manifests       │          │  + delta patches of our       │
│  · news/patches           │          │    mods (pak/lua/sqlite)      │
└───────────┬───────────────┘          └──────────────────────────────┘
            │ heartbeat (player counts, state)
            ▼
┌────────────────────────────────────────────────────────────────────┐
│  SERVER LINES (one per version — AAEmu fork)                      │
│  line 1.2:  AAEmu.Login + AAEmu.Game (develop fork)               │
│  line 3.0:  AAEmu.Login + AAEmu.Game (3.0 fork)                   │
│  each Game reports to the Registry: {version, server, players, state}│
│  + PLUGINS loaded in the Game (event bus + hooks + loader)        │
└────────────────────────────────────────────────────────────────────┘
```

### 2.1 Registry / Metaserver (new, ours)

- Small service (ASP.NET Core — same stack as AAEmu.Login).
- REST endpoints:
  - `GET /versions` → list of supported versions and their state.
  - `GET /versions/{v}/servers` → servers for that version + **live player counts** (the Game sends a heartbeat every N seconds; counts are cached).
  - `GET /versions/{v}/manifest` → client manifest (files, sizes, hashes, chunks) for download/delta patching.
  - `POST /heartbeat` → Game servers register and report state/players.
- **The launcher never touches the archeage client for any of this** — HTTPS only. The client still talks to each version's Login server (original protocol).

### 2.2 Launcher (new, ours) — **[DECISION: stack]**

- **Version selector**: tabs/cards per version (1.2, 3.0...), each with its own server browser.
- **Server browser**: server list with live online players (poll the Registry every ~10s) + state (up/maintenance), optional ping.
- **Client manager**:
  - Download **via manifest**: file list + SHA256 + sizes → download with resume and verification.
  - **Delta patching**: rsync-like by chunks (reference: `Arutosio/Hina`, `meszmate/manifest`) or pak-level patching (reference: `Ingramz/aapatcher`). Our mods = a patch layer over the base client → the player downloads the base once + only the deltas.
  - Integrity verification before launching.
- **Launch**: writes the client config for the chosen version (equivalent to `settings.aelcf`: pathToGame, serverIPAddress → that version's Login, loginType) and launches `archeage.exe`.
- **Accounts**: per-version register/login (each Login server has its own DB) — the launcher can manage per-version credentials.

### 2.3 Server lines (AAEmu fork)

- **One fork, two lines**: `branch 1.2` (develop base, the most maintained) and `branch 3.0` (NL0bP fork base, the "golden age"). **[DECISION: priority order]**
- Server configuration via JSON (already exists: `GameServers` in Config.Local.json) — the Registry *does not* replace this, it only adds to it for the launcher.
- **Heartbeat**: a small service in the Game (or the Login) that reports to the Registry: version, server name, online players, state. It's our code, it doesn't touch the client protocol.

### 2.4 Plugins (new, ours — see INVESTIGACION.md §6)

- Typed event bus + hook points in the managers + **Go plugin model** (dynamic `.so` loading; Lua kept for content scripts — see ADR-001) so the community compiles plugins without cloning the server.
- CI that compiles every catalog plugin against each release (compatibility matrix).
- Plugins run **server-side** (no client changes required). Mods that do touch the client (zones, models, data) travel as **content packs** through the launcher.

---

## 3. Custom content: where each change type lives

| Change type | Where it's implemented | How it reaches the player |
| --- | --- | --- |
| Rules, balance, events, new systems | **Server-side plugin** (Go/Lua) | Nothing to download — the server applies it |
| New items, mobs, quests, NPCs | Server DB (reference `compact.sqlite3` + data) | Server-side; if the client needs assets, content pack |
| Zones ported between versions | `game_pak` (main_world + textures/models) | **Content pack** via launcher (delta over base client) |
| 100% new assets (.cgf/.chr models) | CryEngine 3 toolchain | Content pack via launcher |
| Client UI/QoL | Client Lua + packages | Content pack via launcher |

Rule: **anything that touches the client is a versioned content pack with a manifest**; the launcher applies it as a delta. This way a player with the base 1.2 client downloads only our changes.

---

## 4. Technical workstreams (what needs fixing/building)

### 4.1 Boats / sync / performance (the "green" you saw)

- **Boats**: `BoatPhysicsManager` is WIP in AAEmu (v0.3.0 release notes: "For BoatPhysicsManager", "boat fix"). Physics with Jitter2 + movement packets. Work: physics tuning, client-side interpolation, position packet timing.
- **General sync**: entities/movement/AI — emulators mature this over time; golden packet tests (replaying captures with sequence/timing assertions) turn it into measurable work.
- **Performance**: slow startup (reads `game_pak`), .NET GC, Jitter2 per tick. Work: profiling (dotnet-trace), reference-data caching, async, tick rate tuning.

### 4.2 Protocol / RE (AI loop)

- Capture → decrypt (AES-128-CBC + XOR) → opcode diff between versions → C# structures → golden tests.
- Tools: tshark + `alxbl/archeage` dissector + `OpcodeAndNameFinder` + IDA/Ghidra-MCP.

### 4.3 Tests (the bar)

- Unit (managers), integration (login → create → enter world), **golden packet tests**, system smokes (craft, quest, combat, boat).
- Test-as-bar: a plugin PR doesn't land without tests; a sync fix doesn't land without a golden test.

---

## 5. Repos (monorepo structure)

```text
ArcheaAge/
├── apps/
│   ├── registry/      # metaserver (C# today → Go, Slice 0 of ADR-001)
│   └── launcher/      # launcher app (Rust + Tauri — KEPT as-is)
├── servers/
│   ├── aaemu/         # AAEmu fork (submodule; reference + production during M1-M2)
│   └── go/            # REWRITE in Go — login + game (replaces the fork, ADR-001)
├── sdk/               # plugin API (Go model, see 7.4)
├── plugins/           # plugin catalog (each its own repo/dir + CI)
├── content/           # content packs (manifests + client deltas)
├── tools/             # packer, opcode finder, navmesh, converters, client-sourcing
├── compose.yaml       # dev DB stack (MariaDB); instance definitions come later (M4)
├── db/migrations/     # our own schema migrations
└── docs/              # INVESTIGACION.md, this architecture, guides
```

> This layout is now realized at the repo root: `apps/registry`, `apps/launcher`,
> `servers/aaemu` (fork submodule) and `servers/go` (Slice 0 already building).

---

## 6. Milestones

> Server development track has moved to **Go** (see ADR-001). Milestones below keep the product milestones; the Go rewrite slices are detailed in ADR-001 §4.

1. **M0 (1-2 months)**: set up AAEmu locally (official skill — as protocol/data reference), contribute fixes, decide remaining stack.
2. **M1 (3-6 months)**: **Registry in Go** + launcher v1 (one version, server browser with players, full client download).
3. **M2 (6-12 months)**: Login server in Go (packet protocol 1.2) + network core of Game + first gameplay slice end-to-end.
4. **M3 (12-24 months)**: Game world-scope port (modules by feature slice), plugin layer, second version line (3.0), content packs.
5. **M4 (24+)**: advanced custom content (new zones), anti-cheat, multi-server.

---

## 7. Decisions — **[DECISION]** (decision record in `docs/ADR/`)

1. **Launcher stack**: **Tauri (Rust)** — chosen (see ADR-003).
2. **Flagship version**: 1.2 (AAEmu's most maintained base) — priority, 3.0 later.
3. **Server rewrite language**: **Go** for the new login + game servers (see ADR-001).
4. **Plugin model**: Go plugin loading via dynamic `.so`; Lua kept for content scripts. Details tracked separately (SDK design doc) — **not blocking**, buses/events first.

> Remaining open: launcher+registry detailed spec (start scaffolding), and local AAEmu setup as reference.
