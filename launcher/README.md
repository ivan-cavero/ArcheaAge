# ArcheaAge Launcher

Launcher multi-versión en **Tauri v2** (Rust + web): selector de versión → server browser con jugadores online en vivo → client manager (descarga/parcheo/verificación) → lanzar `archeage.exe`.

## Estado

- **UI moderna**: tema oscuro glassmorphism, selector de versiones con pills, server browser con dots pulsantes y barras de ocupación, barra de progreso por etapas (descarga/verificación/extracción), selector de carpeta de instalación, indicador de conexión al registry.
- **Pipeline completo (Rust)**: `client_ensure` = descargar a temp → verificar SHA256 → extraer con 7-Zip (spanned zip) → instalar en la carpeta elegida → borrar temporales → validar (`game_pak`, `archeage.exe`, `compact.sqlite3`). Descarga desde **Google Drive real** (confirm token + cookies + resume por Range) — probado con `compact.sqlite3` (124 MB, SHA256 verificado).
- **Pendiente (M2)**: merge real de patches a nivel de pak (herramienta aapatcher/AAEmu-Packer), formato exacto `settings.aelcf` del launcher oficial.

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
