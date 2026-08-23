#!/usr/bin/env python3
"""pak_extract.py — extract world cells from an ArcheAge game_pak.

Wraps the existing C# pak-scan tool (tools/pak-scan) via subprocess:

    python tools/world/pak_extract.py <game_pak> <out_dir> <name_filter>

Extracted files keep their in-pak relative paths under <out_dir>.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PAK_SCAN = REPO_ROOT / "tools" / "pak-scan"


def extract(pak: Path, out_dir: Path, name_filter: str) -> int:
    """Run pak-scan and return the number of extracted files."""
    proc = subprocess.run(
        [
            "dotnet",
            "run",
            "--project",
            str(PAK_SCAN),
            "--",
            str(pak),
            str(out_dir),
            name_filter,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"pak-scan failed (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
        )
    # last line: "extracted N file(s) to <out_dir>"
    for line in reversed(proc.stdout.strip().splitlines()):
        if "extracted" in line and "file(s)" in line:
            try:
                return int(line.split()[1])
            except (IndexError, ValueError):
                break
    return 0


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
