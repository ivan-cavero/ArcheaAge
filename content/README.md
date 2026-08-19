# Content packs

Client manifests and custom content that the launcher downloads/applies.

## Structure

```text
content/
├── manifests/          # per-version manifests (served by the Registry)
│   └── 1.2.json
└── packs/              # (future) content deltas: ported zones, mobs, UI
```

## Rules

- **Base** (`manifests/{v}.json.base`): the original client, downloaded once per version (multi-GB, MEGA/Drive via the AAEmu wiki). **Not redistributed** — the launcher downloads it from the CDN/points at the source.
- **Patches**: our changes on top of the base (pak/lua/sqlite) — small deltas.
- **Content packs**: optional per-server custom content (zones ported between versions, new mobs, UI) — the launcher applies them in order: base → patches → chosen server's packs.
- Every file/chunk carries `sha256` → integrity check before launching.

Full schema: `docs/SPEC.md` §2.
