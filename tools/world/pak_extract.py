#!/usr/bin/env python3
"""pak_extract.py — extract world cells from an ArcheAge game_pak.

Uses the Python pak reader (tools.pak). Does not spawn `dotnet run`.

    python tools/world/pak_extract.py <game_pak> <out_dir> <name_filter>
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.pak import open_pak  # noqa: E402


def extract(pak: Path, out_dir: Path, name_filter: str) -> int:
    """Extract entries whose path contains name_filter. Returns count."""
    with open_pak(pak) as gp:
        return gp.extract_matching(out_dir, name_filter)


def extract_cell(pak: Path, world: str, cell: str, out_dir: Path) -> int:
    """Extract one cell (e.g. '003_003') of a world to out_dir."""
    return extract(pak, out_dir, f"{world}/cells/{cell}/client")


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 1
    pak, out_dir, name_filter = sys.argv[1], sys.argv[2], sys.argv[3]
    n = extract(Path(pak), Path(out_dir), name_filter)
    print(f"extracted {n} file(s) to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
