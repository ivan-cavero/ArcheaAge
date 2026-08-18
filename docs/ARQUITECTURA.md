# Arquitectura — "ArcheaAge": launcher multi-versión + fork AAEmu + plugins

> Complementa INVESTIGACION.md. Este doc es el diseño técnico del sistema completo.
> Decisiones abiertas marcadas con **[DECISION]** (ver preguntas al final).

---

## 1. Visión del sistema (lo que el usuario quiere)

1. **Launcher**: abres, eliges **versión** (1.2, 3.0...), ves **lista de servidores** de esa versión con **jugadores online en vivo**, entras → el launcher **descarga/parchea el client necesario** (con nuestras modificaciones) → juegas.
2. **Server open source**: fork de AAEmu (LGPLv3), multi-versión por líneas de branch.
3. **Plugins**: cualquiera puede desarrollar y proponer plugins (modelo AzerothCore).
4. **Contenido custom**: modificar lo original, mejorarlo, añadir zonas y desarrollo nuevo.

---

## 2. Piezas del sistema

```text
┌────────────────────────────────────────────────────────────────────┐
│                        LAUNCHER (cliente)                          │
│  Selector de versión │ Server browser (players online) │ Cliente   │
│  manager (descarga/parchea/verifica) │ Lanza archeage.exe          │
└───────────────┬──────────────────────────────────┬─────────────────┘
                │ HTTPS (API REST)                 │ escribe config del client
                ▼                                  ▼
┌───────────────────────────┐          ┌──────────────────────────────┐
│  REGISTRY / METASERVER    │          │  CLIENT INSTALLS (por versión)│
│  · versiones disponibles  │          │  clients/1.2/  (game_pak,     │
│  · servers por versión    │          │    bin32, compact.sqlite3)    │
│  · player counts (live)   │          │  clients/3.0/  ...            │
│  · manifiestos de client  │          │  + patches delta de nuestros  │
│  · noticias/parches       │          │    mods (pak/lua/sqlite)      │
└───────────┬───────────────┘          └──────────────────────────────┘
            │ heartbeat (player counts, estado)
            ▼
┌────────────────────────────────────────────────────────────────────┐
│  SERVER LINES (una por versión — fork de AAEmu)                    │
│  línea 1.2:  AAEmu.Login + AAEmu.Game (fork develop)               │
│  línea 3.0:  AAEmu.Login + AAEmu.Game (fork 3.0)                   │
│  cada Game reporta al Registry: {version, server, players, estado} │
│  + PLUGINS cargados en el Game (event bus + hooks + loader)        │
└────────────────────────────────────────────────────────────────────┘
```

### 2.1 Registry / Metaserver (nuevo, nuestro)

- Servicio pequeño (ASP.NET Core — mismo stack que AAEmu.Login).
- Endpoints REST:
  - `GET /versions` → lista de versiones soportadas y su estado.
  - `GET /versions/{v}/servers` → servers de esa versión + **player counts en vivo** (el Game envía heartbeat cada N segundos; los counts se cachean).
  - `GET /versions/{v}/manifest` → manifiesto del client (archivos, tamaños, hashes, chunks) para descarga/parcheo delta.
  - `POST /heartbeat` → los Game servers se registran y reportan estado/players.
- **El launcher no toca el client de archeage para nada de esto** — solo HTTPS. El client sigue hablando con el Login server de cada versión (protocolo original).

### 2.2 Launcher (nuevo, nuestro) — **[DECISION: stack]**

- **Selector de versión**: pestañas/cards por versión (1.2, 3.0...), cada una con su server browser.
- **Server browser**: lista de servers con players online en vivo (poll al Registry cada ~10s) + estado (up/maintenance), ping opcional.
- **Client manager**:
  - Descarga **por manifiesto**: lista de archivos + SHA256 + tamaños → descarga con resume y verificación.
  - **Parcheo delta**: rsync-like por chunks (referencia: `Arutosio/Hina`, `meszmate/manifest`) o parcheo a nivel de pak (referencia: `Ingramz/aapatcher`). Nuestros mods = capa de patches sobre el client base → el jugador descarga base una vez + solo los deltas.
  - Verificación de integridad antes de lanzar.
- **Launch**: escribe la config del client para la versión elegida (equivalente a `settings.aelcf`: pathToGame, serverIPAddress → Login de esa versión, loginType) y lanza `archeage.exe`.
- **Cuentas**: registro/login por versión (cada Login server tiene su BD) — el launcher puede gestionar credenciales por versión.

### 2.3 Server lines (fork de AAEmu)

- **Un fork, dos líneas**: `branch 1.2` (base develop, la más mantenida) y `branch 3.0` (base del fork NL0bP, la "edad de oro"). **[DECISION: orden de prioridad]**
- Configuración de servidores por JSON (ya existe: `GameServers` en Config.Local.json) — el Registry *no* sustituye esto, solo lo agrega para el launcher.
- **Heartbeat**: pequeño servicio en el Game (o en el Login) que reporta al Registry: versión, nombre de server, players online, estado. Es código nuestro, no toca el protocolo del client.

### 2.4 Plugins (nuevo, nuestro — ver INVESTIGACION.md §6)

- Event bus tipado + hook points en los managers + loader de módulos (`modules/`, `Assembly.LoadFrom`) + **SDK NuGet** (`ArcheaAge.Sdk`) para que la comunidad compile plugins sin clonar el server.
- CI que compila todos los plugins del catálogo contra cada release (matriz de compatibilidad).
- Los plugins corren **server-side** (no requieren cambios de client). Los mods que sí tocan el client (zonas, modelos, datos) viajan como **content packs** por el launcher.

---

## 3. Contenido custom: dónde vive cada tipo de cambio

| Tipo de cambio | Dónde se implementa | Cómo llega al jugador |
| --- | --- | --- |
| Reglas, balance, eventos, sistemas nuevos | **Plugin server-side** (C#/Lua) | Nada que descargar — el server lo aplica |
| Items, mobs, quests, NPCs nuevos | BD del server (`compact.sqlite3` de referencia + datos) | Server-side; si el client necesita assets, content pack |
| Zonas portadas entre versiones | `game_pak` (main_world + texturas/modelos) | **Content pack** vía launcher (delta sobre client base) |
| Assets 100% nuevos (modelos .cgf/.chr) | Toolchain CryEngine 3 | Content pack vía launcher |
| UI/QoL del client | Lua del client + paquetes | Content pack vía launcher |

Regla: **todo lo que toca el client es un content pack versionado con manifiesto**; el launcher lo aplica como delta. Así un jugador con el client base 1.2 descarga solo nuestros cambios.

---

## 4. Workstreams técnicos (lo que hay que arreglar/hacer)

### 4.1 Barcos / sync / performance (el "verde" que viste)

- **Barcos**: `BoatPhysicsManager` está WIP en AAEmu (notas de release v0.3.0: "For BoatPhysicsManager", "boat fix"). Física con Jitter2 + paquetes de movimiento. Trabajo: tuning de física, interpolación client-side, timing de paquetes de posición.
- **Sync general**: entidades/movimiento/AI — los emuladores maduran esto con el tiempo; los golden tests de paquetes (replay de capturas con aserciones de secuencia/timing) lo convierten en trabajo medible.
- **Performance**: arranque lento (lee `game_pak`), GC de .NET, Jitter2 por tick. Trabajo: profiling (dotnet-trace), caching de datos de referencia, async, tuning de tick rate.

### 4.2 Protocolo / RE (loop de AI)

- Captura → descifrado (AES-128-CBC + XOR) → diff de opcodes entre versiones → estructuras C# → golden tests.
- Herramientas: tshark + disector `alxbl/archeage` + `OpcodeAndNameFinder` + IDA/Ghidra-MCP.

### 4.3 Tests (la barra)

- Unit (managers), integración (login → create → enter world), **golden tests de paquetes**, smoke de sistemas (craft, quest, combate, barco).
- Test-as-bar: un PR de plugin no entra sin tests; un fix de sync no entra sin golden test.

---

## 5. Repos (estructura del monorepo)

```text
ArcheaAge/
├── server/            # fork AAEmu (submodule o subtree), branches 1.2 / 3.0
├── sdk/               # ArcheaAge.Sdk (NuGet) — API de plugins
├── plugins/           # catálogo de plugins (cada uno su repo/dir + CI)
├── registry/          # metaserver (ASP.NET Core)
├── launcher/          # app del launcher (stack por decidir)
├── content/           # content packs (manifiestos + deltas de client)
├── tools/             # packer, opcode finder, navmesh, conversores
└── docs/              # INVESTIGACION.md, esta arquitectura, guías
```

---

## 6. Hitos

1. **M0 (1-2 meses)**: montar AAEmu local (skill oficial), contribuir fixes, decidir stack del launcher.
2. **M1 (3-6 meses)**: Registry + launcher v1 (una versión, server browser con players, descarga de client completo) + fork propio con CI.
3. **M2 (6-12 meses)**: capa de plugins (SDK + loader + CI de compatibilidad) + golden tests de paquetes + primer workstream de barcos/sync.
4. **M3 (12-24 meses)**: segunda línea de versión (3.0), content packs con parcheo delta, catálogo de plugins.
5. **M4 (24+)**: contenido custom avanzado (zonas nuevas), anti-cheat, multi-servidor.

---

## 7. Decisiones abiertas **[DECISION]**

1. **Stack del launcher**: C# (Avalonia/WPF — mismo lenguaje que todo el ecosistema) vs Tauri/Electron (UI web, precedente Minecraft, más bonito, más piezas).
2. **Versión insignia**: 1.2 (base más mantenida de AAEmu, arreglar barcos ahí) vs 3.0 (la "edad de oro", pero fork más viejo y verde).
3. **Siguiente paso**: escribir el spec detallado del launcher+registry y empezar a scaffoldear, o primero montar AAEmu local y validar el flujo.
