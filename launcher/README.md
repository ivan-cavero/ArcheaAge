# ArcheaAge Launcher

Launcher multi-versión en **Tauri v2** (Rust + web): selector de versión → server browser con jugadores online en vivo → client manager (descarga/parcheo/verificación) → lanzar `archeage.exe`.

## Estado

- **UI moderna**: tema oscuro glassmorphism, selector de versiones con pills de estado, server browser con dots de estado pulsantes y barras de ocupación, barra de progreso animada con porcentaje, indicador de conexión al registry.
- **Client manager (Rust)**: `client_ensure` descarga por manifiesto del registry con **resume (HTTP Range)**, verificación SHA256 y eventos `client-progress`; `client_status` comprueba instalación por tamaño; `client_launch` escribe la config del client (`archeaage.config.json`) y lanza `archeage.exe`.
- **Pendiente (M2)**: aplicación de patches del manifiesto (pak/lua/sqlite), formato exacto `settings.aelcf` del launcher oficial.

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
