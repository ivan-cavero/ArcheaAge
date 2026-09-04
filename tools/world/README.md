# tools/world — ArcheAge world data parser

Reads the ArcheAge 1.2 client world (game_pak) into JSON for the 3D editor.

## Pipeline

```text
game_pak ──paklib──▶ cell files + CGF/DDS
                │
                ├─▶ heightmap.py / objects_dat.py / cgf.py / mtl.py
                └─▶ bake_studio.py ─▶ apps/studio/ui/cache (meshes + terrain)
```

## Usage

```bash
# editor bake (heightmaps, CGF meshes, DDS → PNG, vegetation, NPC markers)
python tools/world/bake_studio.py \
  --pak ".client_files/ArcheAge 1.2 (r208022) for AAEmu/game_pak" \
  --world main_world \
  --cells 010_012 010_013 011_011 011_012 011_013 012_012 \
  --out apps/studio/ui/cache

# coarse heightmap of every cell (continent silhouette in the editor)
python tools/world/bake_studio.py \
  --pak ".client_files/ArcheAge 1.2 (r208022) for AAEmu/game_pak" \
  --world main_world --overview \
  --out apps/studio/ui/cache

# one cell -> height JSON only
python tools/world/world_to_json.py \
  --pak ".client_files/ArcheAge 1.2 (r208022) for AAEmu/game_pak" \
  --world arche_mall_world --cells 003_003 004_004 --out out/
```

## Formats (verified against AAEmu source)

### heightmap.dat (CryEngine-style quadtree)

| Offset | Field | Type |
| --- | --- | --- |
| 0 | version/dummy/flags/flags2 | 4 × u8 |
| 4 | chunkSize (file size) | i32 |
| 8 | heightmapSizeInUnits (4096) | i32 |
| 12 | unitSizeInMeters (2) | i32 |
| 16 | sectorSizeInMeters (64) | i32 |
| 20 | sectorsTableSize (128) | i32 |
| 24 | heightmapZRatio (0.0625) | f32 |
| 28 | oceanWaterLevel (100) | f32 |
| 32 | unk (if version >= 24) | 128 bytes |
| 160+ | nodes until chunkSize | NodeCell |

**NodeCell** (repeated): 4×u8 header, AABB (6×f32), bHasHoles (u8),
fOffset (f32), fRange (f32), nSize (i32), unkCount (i32),
nSize×nSize u16 heights, trailing i32 + 4×f32 + 36+unkCount bytes.
If nSize < 33 the node is bilinearly upscaled to 33×33; if version < 7
heights are rescaled to the int grid.

A cell is 16×16 sectors × 32×32 units = **512×512 heights** (1024 m cell,
2 m per unit). Height in meters: `0.05 * iOffset + (raw >> 4) * iStep * 0.05`.

### entities.xml (CryEngine Sandbox)

```xml
<Entity Name="AnimObject_173" Pos="x,y,z" Rotate="w,x,y,z"
        Scale="x,y,z" EntityClass="AnimObject" EntityId="73250" Layer="Main">
  <Properties object_Model="game/objects/env/...ndeco_taegeukgi_long.chr"/>
</Entity>
```

Parsed to: `{name, class, pos:[x,y,z], rotate:[w,x,y,z], scale:[x,y,z],
model, layer, material}`. `object_Model` lives on the `<Properties>` child.

## JSON contract (world_to_json.py output)

```json
{
  "cell": "003_003",
  "heightmap": {"width": 512, "unit_size": 2, "max_height": 4096,
                "water_level": 100, "heights": [[...]]},
  "entities": [{"name": "...", "class": "...", "pos": [x,y,z],
                "rotate": [w,x,y,z], "scale": [x,y,z],
                "model": "...", "layer": "..."}]
}
```

`heights` are meters (float).

### vegetation.dat (4×4 sectors of 256 m)

World groups live in `game/worlds/<world>/vegetation.xml` (`<group id modelFileName fSize>`).
Each cell file starts with version + 16 offsets + 16 sizes, then 64-byte
instances: AABB min/max at 0x00/0x0C, unaligned `uint16` group id at 0x37.

NPC / doodad markers are filtered from AAEmu `npc_spawns.json` / `doodad_spawns.json`.

## Notes

- Reads go through `tools.pak` (Python). `pak_extract.py` no longer
  spawns `dotnet run`. Write/replace of the pak is still `tools/pak-put`.
- Height parsing is a faithful port of AAEmu's `Hmap`/`NodeCell`
  (`servers/aaemu/AAEmu.Game/Models/ClientData/`), so server and editor
  agree on heights.
