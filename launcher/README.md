# ArcheaAge Launcher

Launcher multi-versión en **Tauri v2** (Rust + web): selector de versión → server browser con jugadores online en vivo → client manager (descarga/parcheo/verificación) → lanzar `archeage.exe`.

## Estado

**Scaffold**: el frontend (selector de versiones + server browser) funciona contra el Registry; los comandos Rust (`client_status`, `client_launch`) son stubs — el client manager real (manifiesto, SHA256, parcheo delta) es el workstream M1.

## Dev

```bash
# 1. Registry corriendo (otra terminal)
dotnet run --project ../registry

# 2. Launcher
npm install
npm run tauri dev
```

## Contrato (spec)

- `client_status(version)` → `{ installed, verified, files }`
- `client_launch(version, serverId)` → escribe la config del client (pathToGame, serverIPAddress → Login de la versión, loginType) y lanza `archeage.exe`
- Layout local: `%LOCALAPPDATA%/ArcheaAge/clients/{version}/`

Ver `docs/SPEC.md` §3 para el detalle completo.
