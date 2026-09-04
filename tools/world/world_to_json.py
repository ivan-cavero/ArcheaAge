#!/usr/bin/env python3
"""world_to_json.py — export ArcheAge world cells to JSON for the 3D editor.

  python tools/world/world_to_json.py --pak <game_pak> --world <world> \
      --cells 003_003 004_004 --out <dir>

Produces one JSON file per cell:

  {"cell":"003_003",
   "heightmap": {"width":512, "unit_size":2, "max_height":4096,
                 "water_level":100, "heights":[...]},
   "entities": [{"name":"...", "class":"...", "pos":[x,y,z],
                 "rotate":[w,x,y,z], "scale":[x,y,z], "model":"...",
                 "layer":"..."}]}

heights are raw ushort values; meters = value / height_max_coefficient
(65535 / (max_height/4)).
"""

import argparse
import json
import sys
from pathlib import Path

# Resolve package imports (tools.world.*) when run as a script from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.pak import PakIndex, open_pak  # noqa: E402
from tools.world.entities import parse_entities_text  # noqa: E402
from tools.world.heightmap import (  # noqa: E402
    build_cell_grid,
    default_height_max_coefficient,
    load_heightmap_bytes,
)


def grid_max_height(hmap) -> float:
    """Terrain max height: AAEmu defaults to 4096 (worlds.xml maxTerrainHeight)."""
    return 4096.0


def cell_json(idx: PakIndex, world: str, cell: str) -> dict:
    """Read one cell from the pak, parse it, return the editor JSON contract."""
    base = f"game/worlds/{world}/cells/{cell}/client"
    hraw = idx.read(f"{base}/terrain/heightmap.dat")
    if not hraw:
        raise FileNotFoundError(f"missing heightmap for {world}/{cell}")
    hmap = load_heightmap_bytes(hraw, f"{world}/{cell}/heightmap.dat")
    grid = build_cell_grid(hmap, default_height_max_coefficient(grid_max_height(hmap)))

    entities = []
    xml = idx.read(f"{base}/entities.xml")
    if xml:
        entities = parse_entities_text(xml.decode("utf-8", "replace"))

    return {
        "cell": cell,
        "heightmap": {
            "width": grid["width"],
            "unit_size": grid["unit_size"],
            "max_height": grid["max_height"],
            "water_level": grid["water_level"],
            "heights": grid["heights"],
        },
        "entities": entities,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pak", required=True, help="path to game_pak")
    parser.add_argument(
        "--world", required=True, help="world name, e.g. arche_mall_world"
    )
    parser.add_argument(
        "--cells", nargs="+", required=True, help="cell ids, e.g. 003_003"
    )
    parser.add_argument("--out", required=True, help="output directory")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with open_pak(args.pak) as pak:
        idx = PakIndex(pak)
        for cell in args.cells:
            data = cell_json(idx, args.world, cell)
            target = out / f"{args.world}_{cell}.json"
            target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            print(
                f"wrote {target} ({target.stat().st_size} bytes, {len(data['entities'])} entities)"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
