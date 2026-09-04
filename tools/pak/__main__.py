#!/usr/bin/env python3
"""CLI for read-only game_pak access.

  python -m tools.pak scan    <pak> [filter]
  python -m tools.pak extract <pak> <outDir> [filter]
  python -m tools.pak grep    <pak> <needle> [maxEntrySize]

Write/replace still goes through the C# tool: ``dotnet run --project tools/pak-put``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from tools.pak.paklib import open_pak  # noqa: E402
else:
    from .paklib import open_pak


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m tools.pak")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="list pak entries (optional substring filter)")
    s.add_argument("pak")
    s.add_argument("filter", nargs="?", default=None)

    e = sub.add_parser("extract", help="extract matching entries to outDir")
    e.add_argument("pak")
    e.add_argument("out")
    e.add_argument("filter", nargs="?", default=None)

    g = sub.add_parser("grep", help="search payloads as ASCII and UTF-16LE")
    g.add_argument("pak")
    g.add_argument("needle")
    g.add_argument("max_size", nargs="?", type=int, default=None)

    args = p.parse_args(argv)
    pak = open_pak(args.pak)
    try:
        if args.cmd == "scan":
            entries = pak.list_entries(args.filter)
            print(
                f"entries total: {pak.entry_count}, matching '{args.filter}': {len(entries)}"
            )
            for name, size in entries[:50]:
                print(f"  {name} ({size} bytes)")
            return 0
        if args.cmd == "extract":
            n = pak.extract_matching(args.out, args.filter)
            print(f"extracted {n} file(s) to {args.out}")
            return 0
        if args.cmd == "grep":
            max_size = args.max_size if args.max_size is not None else 2**63 - 1
            hits = pak.grep(args.needle, max_size=max_size)
            for name, size in hits:
                print(f"HIT {name} ({size} bytes)")
            print(f"done: {len(hits)} hit(s)")
            return 0
    finally:
        pak.close()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
