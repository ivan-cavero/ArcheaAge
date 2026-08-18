# Content packs

Manifiestos de client y contenido custom que el launcher descarga/aplica.

## Estructura

```text
content/
├── manifests/          # manifiestos por versión (los sirve el Registry)
│   └── 1.2.json
└── packs/              # (futuro) deltas de contenido: zonas portadas, mobs, UI
```

## Reglas

- **Base** (`manifests/{v}.json.base`): el client original, descargado una vez por versión (multi-GB, MEGA/Drive vía wiki de AAEmu). **No se redistribuye** — el launcher lo descarga del CDN/apunta a la fuente.
- **Patches**: nuestros cambios sobre el base (pak/lua/sqlite) — deltas pequeños.
- **Content packs**: contenido custom opcional por servidor (zonas portadas entre versiones, mobs nuevos, UI) — el launcher los aplica en orden: base → patches → packs del server elegido.
- Cada archivo/chunk lleva `sha256` → verificación de integridad antes de lanzar.

Esquema completo: `docs/SPEC.md` §2.
