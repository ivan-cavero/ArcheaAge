# apps/studio — ArcheaAge Editor

World viewport + UI tools. The 3D world is the home screen; the old UI
layout editor is a mode, not the landing page.

Frontend is static (`ui/`, no bundler). `withGlobalTauri` exposes
`window.__TAURI__` for invoke. The 3D viewport is split across
`ui/js/viewport.js` (camera/loop) + `environment.js` + `assets.js` +
`terrain.js` + `entities.js`.

`ui/worlds.json` is the committed world catalog (which cells/regions exist).
`ui/cache/` and `ui/cells/` are generated and gitignored.

## Run (dev)

```powershell
cd apps\studio
npm install
npm run dev
```

(`npm run dev` is `tauri dev`. First run compiles the Rust crate ~2–5 min;
later runs are fast.)

To preview just the web UI (no Tauri):

```powershell
cd apps\studio\ui
python -m http.server 5178
# open http://127.0.0.1:5178
```

## World data

World data is baked from `game_pak` (heightmaps, CGF meshes, DDS textures):

```powershell
python tools/world/bake_studio.py `
  --pak ".client_files/ArcheAge 1.2 (r208022) for AAEmu/game_pak" `
  --world main_world `
  --cells 010_012 010_013 011_011 011_012 011_013 012_012 `
  --out apps/studio/ui/cache

python tools/world/bake_studio.py `
  --pak ".client_files/ArcheAge 1.2 (r208022) for AAEmu/game_pak" `
  --world main_world --overview `
  --out apps/studio/ui/cache
```

`ui/cache/` and `ui/cells/` are gitignored. `ui/worlds.json` is the catalog.

Home / Overview shows the continent silhouette (coarse heights). The camera
starts at walking height in the first catalog cell, not in the sky.

## Controls

| Input | Action |
| --- | --- |
| RMB + drag | Look |
| RMB + WASD / QE | Fly (Shift = faster) |
| LMB | Select entity |
| MMB | Pan |
| Wheel | Zoom |
| W / E / R | Move / rotate / scale gizmo (when not flying) |
| F | Frame selection |
| G | Toggle grid |

Volumes (audio, area shapes) are hidden until **Volumes** is checked.

## Notes

- Terrain is real heightmap metres, origin at the cell corner. No Z exaggeration.
- Brushes are CGF from `object.dat`. Plants/trees come from `vegetation.dat`.
- Yellow capsules are NPC spawns from AAEmu `npc_spawns.json`; small boxes are doodads.
