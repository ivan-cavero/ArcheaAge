# ArcheaAge

Servidor privado de **ArcheAge** open source: fork de [AAEmu](https://github.com/AAEmu/AAEmu) (LGPLv3), launcher multi-versión, plugins comunitarios y contenido custom.

> **Estado**: investigación + spec + scaffold inicial. Ver `docs/INVESTIGACION.md` (el porqué), `docs/ARQUITECTURA.md` (el qué) y `docs/SPEC.md` (el contrato técnico).

## Visión

1. **Launcher** (Tauri): eliges versión → ves servidores con jugadores online → descarga/parchea el client (con nuestras modificaciones) → juegas.
2. **Server** open source: fork de AAEmu, versión insignia **1.2**, línea **3.0** ("edad de oro") después.
3. **Plugins**: cualquiera desarrolla y propone plugins (modelo AzerothCore) vía `ArcheaAge.Sdk`.
4. **Contenido custom**: modificar lo original, mejorarlo, añadir zonas y desarrollo nuevo (content packs vía launcher).

## Estructura

```text
registry/   # Metaserver ASP.NET Core: versiones, servers, players online, manifiestos
sdk/        # ArcheaAge.Sdk — contrato de plugins (NuGet, sin dependencia de AAEmu)
plugins/    # Catálogo de plugins (Example incluido)
launcher/   # Tauri v2 (Rust + web): selector de versión + server browser + client manager
content/    # Manifiestos de client y content packs
server/     # Fork de AAEmu — submodule, ver abajo
docs/       # Investigación, arquitectura, spec
```

## Arranque rápido

### Registry (requiere .NET 10)

```bash
dotnet run --project registry
# GET http://localhost:5080/versions
```

### SDK + plugins

```bash
dotnet build sdk
dotnet build plugins/Example
```

### Launcher (requiere Rust + Node)

```bash
cd launcher
npm install
npm run tauri dev
```

### Server (fork de AAEmu)

```bash
git submodule update --init server   # clona el fork
# seguir la skill oficial de setup: .agents/skills/aaemu-setup (docs en el submodule)
```

## Licencia

Código del server: LGPLv3 (igual que AAEmu). Código propio (registry, sdk, launcher, content): LGPLv3.
El client de ArcheAge y los datos del juego son propiedad de XLGAMES — no se redistribuyen. No afiliado con XLGAMES.
