# ArcheaAge

Open source private **ArcheAge** server: fork of [AAEmu](https://github.com/AAEmu/AAEmu) (LGPLv3), multi-version launcher, community plugins and custom content.

> **Status**: research + spec + initial scaffold. See `docs/INVESTIGACION.md` (the why), `docs/ARQUITECTURA.md` (the what) and `docs/SPEC.md` (the technical contract).

## Vision

1. **Launcher** (Tauri): pick a version → see servers with online players → download/patch the client (with our modifications) → play.
2. **Server** open source: AAEmu fork, flagship version **1.2**, **3.0** line ("golden age") later.
3. **Plugins**: anyone develops and proposes plugins (AzerothCore model) via `ArcheaAge.Sdk`.
4. **Custom content**: modify the original, improve it, add zones and new development (content packs via the launcher).

## Structure

```text
registry/   # ASP.NET Core metaserver: versions, servers, online players, manifests
sdk/        # ArcheaAge.Sdk — plugin contract (NuGet, no AAEmu dependency)
plugins/    # Plugin catalog (Example included)
launcher/   # Tauri v2 (Rust + web): version selector + server browser + client manager
content/    # Client manifests and content packs
server/     # AAEmu fork — submodule, see below
docs/       # Research, architecture, spec
```

## Quick start

### Registry (requires .NET 10)

```bash
dotnet run --project registry
# GET http://localhost:5080/versions
```

### SDK + plugins

```bash
dotnet build sdk
dotnet build plugins/Example
```

### Launcher (requires Rust + Node)

```bash
cd launcher
npm install
npm run tauri dev
```

### Server (AAEmu fork)

```bash
git submodule update --init server   # clones the fork
# follow the official setup skill: .agents/skills/aaemu-setup (docs in the submodule)
```

## License

Server code: LGPLv3 (same as AAEmu). Own code (registry, sdk, launcher, content): LGPLv3.
The ArcheAge client and game data are property of XLGAMES — not redistributed. Not affiliated with XLGAMES.
