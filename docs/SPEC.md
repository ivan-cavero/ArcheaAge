# Spec — Registry, Launcher y SDK de plugins

> Decisiones bloqueadas: launcher en **Tauri (Rust + web)**, versión insignia **1.2**, arranque por **spec + scaffold**.
> Este doc es el contrato técnico. Los archivos de scaffold implementan esta spec.

---

## 1. Registry / Metaserver (ASP.NET Core, minimal API)

Servicio central que el launcher consulta. **No** participa en el protocolo del juego.

### 1.1 Endpoints

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/health` | Liveness para el launcher/CI |
| `GET` | `/versions` | Versiones soportadas + resumen (nombre, client, estado) |
| `GET` | `/versions/{version}/servers` | Servers de la versión con **players online en vivo** |
| `GET` | `/versions/{version}/manifest` | Manifiesto del client (archivos, hashes, chunks, patches, content packs) |
| `POST` | `/heartbeat` | Los Game servers reportan estado + players (auth por token) |

### 1.2 Modelo de datos

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

// POST /heartbeat  (Game → Registry, cada 15s)
{
  "token": "xxx",                          // secreto compartido por versión
  "version": "1.2",
  "serverId": "eu-1",
  "serverName": "ArcheaAge EU-1",
  "players": 84,
  "maxPlayers": 500,
  "status": "online"
}
```

### 1.3 Estado

- **En memoria** (ConcurrentDictionary) para el scaffold: heartbeat actualiza la entrada; entrada sin heartbeat en 60s → `offline`.
- **Migración futura**: MySQL (mismo stack que AAEmu) cuando haya historial/métricas. `ponytail: in-memory first, MySQL when metrics/history matter`.

### 1.4 Seguridad

- `/heartbeat` requiere `Authorization: Bearer <token>` (token por versión en configuración).
- Endpoints de lectura públicos (el launcher no tiene cuentas propias de momento).
- CORS abierto solo al origen del launcher dev.

---

## 2. Manifiesto de client (content/)

El contrato entre Registry y el client manager del launcher.

```jsonc
// content/manifests/1.2.json
{
  "version": "1.2",
  "client": "1.2.4.0 (r208022)",
  "base": {
    // client base original — el jugador lo descarga una vez (multi-GB)
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
    // nuestros cambios sobre el base — delta que el launcher aplica
    { "path": "game_pak", "type": "pak", "url": "https://cdn.archeaage.dev/1.2/patches/mods-1.2.1.pak", "sha256": "…" }
  ],
  "contentPacks": [
    // contenido custom (zonas portadas, mobs, UI) — opcional por servidor
    { "id": "zones-hiram-port", "version": "1.0", "files": [ { "path": "game_pak", "type": "pak", "url": "…", "sha256": "…" } ] }
  ],
  "login": { "protocol": "trino_1_2" }     // loginType que escribe el launcher
}
```

Reglas:

- **Base se descarga una vez** por versión; los patches/content packs son deltas pequeños.
- Cada archivo/chunk tiene `sha256` → verificación de integridad antes de lanzar.
- El launcher aplica: base → patches → content packs del servidor elegido, en ese orden.

---

## 3. Launcher (Tauri v2, Rust + web)

### 3.1 Pantallas (v1)

1. **Selector de versión**: cards con las versiones del Registry (nombre, client, estado, players totales).
2. **Server browser** (por versión): lista de servers con players online en vivo (poll al Registry cada 10s), estado, botón "Jugar".
3. **Client manager**: progreso de descarga/parcheo (base → patches → content packs), verificación SHA256, resume.
4. **Launch**: escribe la config del client para la versión (pathToGame, serverIPAddress → Login de esa versión, loginType) y lanza `archeage.exe`.

### 3.2 Comandos Tauri (Rust)

| Comando | Entrada | Salida | Notas |
| --- | --- | --- | --- |
| `registry_get` | `path` | JSON | Proxy HTTP al Registry (evita CORS en producción) |
| `client_ensure` | `version`, `serverId` | `{ status, progress }` | Descarga/parchea/verifica; eventos de progreso al frontend |
| `client_status` | `version` | `{ installed, verified, files }` | Estado local |
| `client_launch` | `version`, `server` | `{ ok }` | Escribe `settings.aelcf`-equivalente y lanza `archeage.exe` |

### 3.3 Layout local (Windows)

```text
%LOCALAPPDATA%/ArcheaAge/
├── clients/
│   ├── 1.2/          # instalación por versión
│   │   ├── game_pak
│   │   ├── bin32/archeage.exe
│   │   └── compact.sqlite3
│   └── 3.0/          # (futuro)
├── config.json       # versiones/servers recordados, credenciales por versión
└── logs/
```

---

## 4. SDK de plugins (ArcheaAge.Sdk, .NET)

Contrato mínimo para que un plugin compile **sin clonar el server** (paquete NuGet `ArcheaAge.Sdk`).

```csharp
namespace ArcheaAge.Sdk;

/// <summary>Contrato de un plugin. El server carga ensamblados que implementan IAaPlugin.</summary>
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

/// <summary>Bus de eventos tipado. El server publica eventos; los plugins se suscriben.</summary>
public interface IEventBus
{
    void Subscribe<T>(Action<T> handler) where T : GameEvent;
    void Unsubscribe<T>(Action<T> handler) where T : GameEvent;
    void Publish<T>(T evt) where T : GameEvent;
}

public abstract record GameEvent(DateTime OccurredAt);

// Eventos de ejemplo (el server los publica en sus managers)
public sealed record PlayerLoggedIn(long AccountId, long CharacterId, string Name) : GameEvent(DateTime.UtcNow);
public sealed record QuestCompleted(long CharacterId, uint QuestId) : GameEvent(DateTime.UtcNow);
public sealed record ItemCrafted(long CharacterId, uint ItemTemplateId, int Count) : GameEvent(DateTime.UtcNow);
```

Reglas:

- El SDK **no referencia AAEmu** (contrato puro) → el adaptador server-side (que traduce eventos de AAEmu al bus) vive en el fork, no en el SDK.
- Versionado semántico del SDK; el server carga plugins compatibles con su versión de SDK.
- El loader (`Assembly.LoadFrom` + reflexión sobre `IAaPlugin`) se implementa en el fork (workstream M2).

---

## 5. Estructura del monorepo (scaffold)

```text
ArcheaAge/
├── README.md
├── .gitmodules            # server/ → AAEmu (submodule, sin clonar aún)
├── .github/workflows/ci.yml
├── docs/                  # INVESTIGACION.md, ARQUITECTURA.md, SPEC.md
├── registry/              # ArcheaAge.Registry (ASP.NET Core minimal API)
├── sdk/                   # ArcheaAge.Sdk (contrato de plugins, NuGet)
├── plugins/
│   ├── README.md
│   └── Example/           # ArcheaAge.Plugins.Example (referencia el SDK)
├── launcher/              # Tauri v2 (Rust + web)
│   ├── index.html, src/, vite.config.js, package.json
│   └── src-tauri/         # Cargo.toml, tauri.conf.json, src/
└── content/
    ├── README.md
    └── manifests/1.2.json # manifest de ejemplo
```

- `server/` es un **submodule** (`git submodule update --init`) — no se clona en el scaffold.
- CI: `dotnet build/test` (registry + sdk + plugins) y `cargo check` (launcher).

---

## 6. Fuera de alcance del scaffold (workstreams futuros)

- Fix de barcos/sync/performance en el fork (M2+).
- Línea de versión 3.0 (M3+).
- Loader de plugins dentro del fork + adaptador de eventos (M2).
- Anti-cheat, cuentas propias, CDN real, multi-servidor (M4+).
