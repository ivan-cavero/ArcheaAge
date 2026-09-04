#!/usr/bin/env python3
"""decompile.py — batch-decompile .alb files from an ArcheAge game_pak to Lua.

Subcommands:
  all      decompile EVERY .alb in the pak to tools/ui/src/  (default flow)
  module   decompile one scriptsbin/x2ui/<NAME> subtree to tools/ui/decompiled/

Backend: unluac.jar (Java). Verified best tool for this client's Lua 5.1
float (32-bit) bytecode: 956/966 .alb decompile cleanly; the 10 failures are
empty 60-byte stubs (chunks with no code) and are skipped silently.

Examples:
  python tools/ui/decompile.py all
  python tools/ui/decompile.py module loginstage
  python tools/ui/decompile.py --client-dir <dir> all
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CLIENT_DIR = Path(".client_files") / "ArcheAge 1.2 (r208022) for AAEmu"
DEFAULT_DECOMPILER = Path(__file__).resolve().parent / "unluac.jar"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.pak import open_pak  # noqa: E402


def resolve_pak(args: argparse.Namespace) -> Path:
    """game_pak path from --pak or --client-dir, with a clear error."""
    pak = Path(args.pak) if args.pak else Path(args.client_dir) / "game_pak"
    if not pak.exists():
        raise RuntimeError(f"game_pak not found: {pak} (pass --client-dir or --pak)")
    return pak


def resolve_decompiler(args: argparse.Namespace) -> Path:
    """unluac jar path from --decompiler, with a clear error."""
    jar = Path(args.decompiler)
    if not jar.exists():
        raise RuntimeError(
            f"decompiler jar not found: {jar} (pass --decompiler or restore tools/ui/unluac.jar)"
        )
    return jar


def extract_albs(pak: Path, out_dir: Path, filter_str: str, no_print: bool) -> list[Path]:
    """Extract matching pak entries under out_dir; return .alb paths."""
    del no_print  # kept in signature for callers; listing is no longer printed
    with open_pak(pak) as gp:
        n = gp.extract_matching(out_dir, filter_str)
    if n == 0:
        raise RuntimeError(f"no pak entries matching '{filter_str}' in {pak}")
    return sorted(out_dir.rglob("*.alb"))


def decompile_one(alb: Path, out: Path, jar: Path, java: str) -> str:
    """Decompile one .alb to .lua. Returns 'ok', 'skip' (empty stub) or 'fail'."""
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [java, "-jar", str(jar), "-o", str(out), str(alb)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        raise RuntimeError(
            f"java executable not found: '{java}' (install a JRE/JDK or pass --java)"
        ) from None
    if proc.returncode != 0:
        return "fail"
    # exit 0 with empty/no output = empty chunk stub, not an error
    return "ok" if out.exists() and out.stat().st_size > 0 else "skip"


def decompile_batch(
    albs: list[Path], extract_root: Path, out_root: Path,
    jar: Path, java: str, quiet: bool,
) -> tuple[int, int, int]:
    """Decompile every .alb, mirroring pak paths under out_root. Returns (ok, skip, fail)."""
    ok = skip = fail = 0
    total = len(albs)
    for i, alb in enumerate(albs, 1):
        rel = alb.relative_to(extract_root)
        out = out_root / rel.with_suffix(".lua")
        result = decompile_one(alb, out, jar, java)
        if result == "ok":
            ok += 1
        elif result == "skip":
            skip += 1
        else:
            fail += 1
        if not quiet and i % 100 == 0:
            print(f"  {i}/{total}...")
    return ok, skip, fail


def cmd_all(args: argparse.Namespace) -> None:
    """Decompile every .alb in the pak to tools/ui/src/ (mirrors pak structure)."""
    pak = resolve_pak(args)
    jar = resolve_decompiler(args)
    if not args.quiet:
        print("extracting all .alb files...")
    with tempfile.TemporaryDirectory(prefix="aa_alb_") as tmp:
        extract_root = Path(tmp)
        albs = extract_albs(pak, extract_root, ".alb", no_print=True)
        if not args.quiet:
            print(f"found {len(albs)} .alb files")
        out_root = REPO_ROOT / "tools" / "ui" / "src"
        out_root.mkdir(parents=True, exist_ok=True)
        ok, skip, fail = decompile_batch(albs, extract_root, out_root, jar, args.java, args.quiet)
    suffix = f" ({skip} empty stubs skipped)" if skip else ""
    print(f"done: ok={ok} fail={fail}{suffix}")


def cmd_module(args: argparse.Namespace) -> None:
    """Decompile one scriptsbin/x2ui/<NAME> subtree to tools/ui/decompiled/."""
    pak = resolve_pak(args)
    jar = resolve_decompiler(args)
    name = args.name or "loginstage"
    filter_str = f"scriptsbin/x2ui/{name}"
    with tempfile.TemporaryDirectory(prefix="aa_alb_") as tmp:
        extract_root = Path(tmp)
        albs = extract_albs(pak, extract_root, filter_str, no_print=False)
        if not args.quiet:
            print(f"found {len(albs)} .alb files for module '{name}'")
        out_root = Path(__file__).resolve().parent / "decompiled"
        out_root.mkdir(parents=True, exist_ok=True)
        ok, skip, fail = decompile_batch(albs, extract_root, out_root, jar, args.java, args.quiet)
    suffix = f" ({skip} empty stubs skipped)" if skip else ""
    print(f"decompiled ok={ok} fail={fail}{suffix} -> {out_root}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="decompile.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--client-dir", default=str(DEFAULT_CLIENT_DIR),
        help=f"client install dir containing game_pak (default: {DEFAULT_CLIENT_DIR})",
    )
    parser.add_argument(
        "--pak", default=None,
        help="game_pak path (overrides --client-dir)",
    )
    parser.add_argument(
        "--decompiler", default=str(DEFAULT_DECOMPILER),
        help=f"unluac jar path (default: {DEFAULT_DECOMPILER})",
    )
    parser.add_argument("--java", default="java", help="java executable (default: java)")
    parser.add_argument("--quiet", action="store_true", help="suppress progress output")

    sub = parser.add_subparsers(dest="command", required=True)
    p_all = sub.add_parser("all", help="decompile EVERY .alb in the pak to tools/ui/src/")
    p_all.set_defaults(func=cmd_all)
    p_mod = sub.add_parser(
        "module",
        help="decompile one scriptsbin/x2ui/<NAME> subtree to tools/ui/decompiled/",
    )
    p_mod.add_argument(
        "name", nargs="?", default="loginstage",
        help="module subtree name under scriptsbin/x2ui/ (default: loginstage)",
    )
    p_mod.set_defaults(func=cmd_module)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
