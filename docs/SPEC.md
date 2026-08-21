# Spec — Registry, Launcher and plugin SDK

> Locked decisions: launcher on **Tauri (Rust + web)**, flagship version **1.2**, start via **spec + scaffold**.
> This document is the technical contract. The scaffold files implement this spec.

---

## 1. Registry / Metaserver (ASP.NET Core, minimal API)

Central service the launcher queries. It does **not** participate in the game protocol.

### 1.1 Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Liveness for the launcher/CI |
| `GET` | `/versions` | Supported versions + summary (name, client, state) |
| `GET` | `/versions/{version}/servers` | Servers for the version with **live online players** |
| `GET` | `/versions/{version}/manifest` | Client manifest (files, hashes, chunks, patches, content packs) |
| `GET` | `/news` | Launcher news feed (`content/news.json`) |
| `POST` | `/heartbeat` | Game servers report state + players (token auth) |

### 1.2 Data model

```jsonc
// GET /versions
{
  "versions": [
    {
      "id": "1.2",
      "name": "ArcheAge 1.2 (launch era)",
      "client": "1.2.4.0 (r208022)",
      "status": "live",                    // live | beta | maintenance | planned
      "servers": 2,
      "playersOnline": 137,
      "downloadSize": 8941130695,          // total bytes to download (hero display)
      "manifestUrl": "/versions/1.2/manifest"
    }
  ]
}

// GET /versions/1.2/servers
{
  "servers": [
    {
      "id": "eu-1",
      "name": "ArcheaAge EU-1",
      "host": "play.eu.archeaage.dev",
      "status": "online",                  // online | maintenance | full
      "players": 84,
      "maxPlayers": 500,
      "uptimeSeconds": 3600,
      "lastHeartbeat": "2026-08-18T20:00:00Z"
    }
  ]
}

// POST /heartbeat  (Game → Registry, every 15s)
{
  "token": "xxx",                          // shared secret per version
  "version": "1.2",
  "serverId": "eu-1",
  "serverName": "ArcheaAge EU-1",
  "players": 84,
  "maxPlayers": 500,
  "status": "online"
}
```

### 1.3 State

- **In-memory** (ConcurrentDictionary) for the scaffold: a heartbeat updates the entry; an entry without a heartbeat in 60s → `offline`.
- **Future migration**: MySQL (same stack as AAEmu) when there's history/metrics. `ponytail: in-memory first, MySQL when metrics/history matter`.

### 1.4 Security

- `/heartbeat` requires `Authorization: Bearer <token>` (per-version token in configuration).
- Read endpoints are public (the launcher has no accounts of its own for now).
- CORS open only to the launcher dev origin.

---

## 2. Client manifest (content/)

The contract between the Registry and the launcher's client manager.

```jsonc
// content/manifests/1.2.json
{
  "version": "1.2",
  "client": "1.2.4.0 (r208022)",
  "base": {
    // original base client — the player downloads it once (multi-GB)
    "source": "https://cdn.archeaage.dev/1.2/base/",
    "files": [
      {
        "path": "game_pak",
        "size": 8589934592,
        "sha256": "…",
        "chunks": [ { "index": 0, "size": 4194304, "sha256": "…" } ]
      }
      // bin32/archeage.exe, compact.sqlite3, …
    ]
  },
  "patches": [
    // our changes over the base — the delta the launcher applies
    { "path": "game_pak", "type": "pak", "url": "https://cdn.archeaage.dev/1.2/patches/mods-1.2.1.pak", "sha256": "…" }
  ],
  "contentPacks": [
    // custom content (ported zones, mobs, UI) — optional per server
    { "id": "zones-hiram-port", "version": "1.0", "files": [ { "path": "game_pak", "type": "pak", "url": "…", "sha256": "…" } ] }
  ],
  "login": { "protocol": "trino_1_2" }     // loginType the launcher writes
}
```

Rules:

- **Base is downloaded once** per version; patches/content packs are small deltas.
- Every file/chunk has `sha256` → integrity check before launching.
- The launcher applies: base → patches → chosen server's content packs, in that order.

---

## 3. Launcher (Tauri v2, Rust + web)

### 3.1 Screens (v1)

1. **Version selector**: cards with the Registry's versions (name, client, state, total players).
2. **Server browser** (per version): server list with live online players (poll the Registry every 10s), state, "Play" button.
3. **Client manager**: download/patch progress (base → patches → content packs), SHA256 verification, resume.
4. **Launch**: writes the client config for the version (pathToGame, serverIPAddress → that version's Login, loginType) and launches `archeage.exe`.

### 3.2 Tauri commands (Rust)

| Command | Input | Output | Notes |
| --- | --- | --- | --- |
| `registry_get` | `path` | JSON | HTTP proxy to the Registry (avoids CORS in production) |
| `client_ensure` | `version`, `serverId` | `{ status, progress }` | Download/patch/verify; progress events to the frontend |
| `client_status` | `version` | `{ installed, verified, files }` | Local state |
| `client_launch` | `version`, `server` | `{ ok }` | Writes `settings.aelcf`-equivalent and launches `archeage.exe` |

### 3.3 Local layout (Windows)

```text
%LOCALAPPDATA%/ArcheaAge/
├── clients/
│   ├── 1.2/          # per-version install
│   │   ├── game_pak
│   │   ├── bin32/archeage.exe
│   │   └── compact.sqlite3
│   └── 3.0/          # (future)
├── config.json       # remembered versions/servers, per-version credentials
└── logs/
```

---

## 4. Plugin SDK (ArcheaAge.Sdk, .NET)

Minimal contract so a plugin compiles **without cloning the server** (NuGet package `ArcheaAge.Sdk`).

```csharp
namespace ArcheaAge.Sdk;

/// <summary>Plugin contract. The server loads assemblies implementing IAaPlugin.</summary>
public interface IAaPlugin
{
    string Id { get; }          // "dev.archeaage.tradepack-tweaks"
    string Name { get; }
    string Version { get; }
    void OnLoad(IPluginContext context);
    void OnUnload();
}

public interface IPluginContext
{
    IEventBus Events { get; }
    ILogger Logger { get; }
}

/// <summary>Typed event bus. The server publishes events; plugins subscribe.</summary>
public interface IEventBus
{
    void Subscribe<T>(Action<T> handler) where T : GameEvent;
    void Unsubscribe<T>(Action<T> handler) where T : GameEvent;
    void Publish<T>(T evt) where T : GameEvent;
}

public abstract record GameEvent(DateTime OccurredAt);

// Example events (the server publishes them from its managers)
public sealed record PlayerLoggedIn(long AccountId, long CharacterId, string Name) : GameEvent(DateTime.UtcNow);
public sealed record QuestCompleted(long CharacterId, uint QuestId) : GameEvent(DateTime.UtcNow);
public sealed record ItemCrafted(long CharacterId, uint ItemTemplateId, int Count) : GameEvent(DateTime.UtcNow);
```

Rules:

- The SDK **does not reference AAEmu** (pure contract) → the server-side adapter (translating AAEmu events to the bus) lives in the fork, not in the SDK.
- Semantic versioning of the SDK; the server loads plugins compatible with its SDK version.
- The loader (`Assembly.LoadFrom` + reflection over `IAaPlugin`) is implemented in the fork (workstream M2).

---

## 5. Monorepo structure (scaffold)

```text
ArcheaAge/
├── README.md
├── .gitmodules            # server/ → AAEmu (submodule, not cloned yet)
├── .github/workflows/ci.yml
├── docs/                  # INVESTIGACION.md, ARQUITECTURA.md, SPEC.md
├── registry/              # ArcheaAge.Registry (ASP.NET Core minimal API)
├── sdk/                   # ArcheaAge.Sdk (plugin contract, NuGet)
├── plugins/
│   ├── README.md
│   └── Example/           # ArcheaAge.Plugins.Example (references the SDK)
├── launcher/              # Tauri v2 (Rust + web)
│   ├── index.html, src/, vite.config.js, package.json
│   └── src-tauri/         # Cargo.toml, tauri.conf.json, src/
└── content/
    ├── README.md
    └── manifests/1.2.json # example manifest
```

- `server/` is a **submodule** (`git submodule update --init`) — not cloned in the scaffold.
- CI: `dotnet build/test` (registry + sdk + plugins) and `cargo check` (launcher).

---

## 6. Out of scaffold scope (future workstreams)

- Boat/sync/performance fixes in the fork (M2+).
- 3.0 version line (M3+).
- Plugin loader inside the fork + event adapter (M2).
- Anti-cheat, own accounts, real CDN, multi-server (M4+).