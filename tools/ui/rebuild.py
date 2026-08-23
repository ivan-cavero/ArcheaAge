#!/usr/bin/env python3
"""rebuild.py — compiles modified .lua files and injects them into game_pak.

Port of rebuild.ps1 to Python.

  python tools/ui/rebuild.py                     # recompile all changed
  python tools/ui/rebuild.py --file path.lua     # single file

Flow: edit tools/ui/src/**/*.lua -> rebuild.py -> reopen the game.
The compiled .alb replaces the original entry in game_pak (pak-put).
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
UI_DIR = Path(__file__).resolve().parent
SRC_DIR = (UI_DIR / "src").resolve()


def run(cmd, description):
    """Run a command, print its output, raise with stderr on failure."""
    print("  " + " ".join(str(c) for c in cmd))
    proc = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"{description} failed (exit {proc.returncode})\n{err}")
    return out


def stop_game_server():
    """Kill a running AAEmu.Game dotnet process so the pak file is unlocked."""
    ps = (
        "powershell -NoProfile -Command "
        '"Get-CimInstance Win32_Process -Filter \\"Name=\'dotnet.exe\'\\" | '
        "Where-Object { $_.CommandLine -match 'AAEmu\\.Game\\.dll' } | "
        'ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"'
    )
    proc = subprocess.run(ps, capture_output=True, text=True)
    if proc.returncode == 0 and proc.stdout.strip():
        print("Game stopped for injection")
    import time

    time.sleep(2)


def compile_lua(luac, src, out):
    run([luac, "-o", out, src], "compile")


def pak_put(pak, local, entry):
    project = REPO_ROOT / "tools" / "pak-put"
    run(
        ["dotnet", "run", "--project", project, "--", pak, local, entry],
        f"pak-put for {entry}",
    )


def rebuild_single(pak, luac, file_path):
    file_path = Path(file_path).resolve()
    rel = file_path.relative_to(SRC_DIR).as_posix()
    if not rel.endswith(".lua"):
        raise RuntimeError(f"not a .lua file: {file_path}")
    alb_entry = rel[:-4] + ".alb"
    tmp_alb = Path(tempfile.gettempdir()) / "rebuild_tmp.alb"

    compile_lua(luac, file_path, tmp_alb)
    pak_put(pak, tmp_alb, alb_entry)
    print(f"injected: {alb_entry}")


def rebuild_batch(pak, luac):
    tmp_dir = Path(tempfile.gettempdir())
    changed = []
    for f in SRC_DIR.rglob("*.lua"):
        rel = f.relative_to(SRC_DIR).as_posix()
        marker = tmp_dir / ("rebuild_" + rel.replace("/", "\\"))
        if not marker.exists() or f.stat().st_mtime > marker.stat().st_mtime:
            changed.append(f)
    print(f"{len(changed)} files to compile")

    for f in changed:
        rel = f.relative_to(SRC_DIR).as_posix()
        alb_entry = rel[:-4] + ".alb"
        tmp_alb = tmp_dir / ("rebuild_" + f.name + ".alb")
        try:
            compile_lua(luac, f, tmp_alb)
        except RuntimeError:
            print(f"SKIP (compile error): {rel}")
            continue
        pak_put(pak, tmp_alb, alb_entry)
    print("batch done.")


def main():
    parser = argparse.ArgumentParser(
        description="Compile modified .lua and inject into game_pak"
    )
    parser.add_argument("--file", default=None, help="single .lua file to rebuild")
    parser.add_argument(
        "--client-dir",
        default=".client_files/ArcheAge 1.2 (r208022) for AAEmu",
        help="client directory containing game_pak",
    )
    parser.add_argument(
        "--pak", default=None, help="path to game_pak (default <client-dir>/game_pak)"
    )
    parser.add_argument(
        "--luac",
        default=None,
        help="path to luac5f.exe (default tools/ui/luac-build/luac5f.exe)",
    )
    args = parser.parse_args()

    pak = Path(args.pak) if args.pak else Path(args.client_dir) / "game_pak"
    luac = Path(args.luac) if args.luac else UI_DIR / "luac-build" / "luac5f.exe"

    if not pak.exists():
        raise RuntimeError(f"game_pak not found: {pak}")
    if not luac.exists():
        raise RuntimeError(
            f"luac5f.exe not found ({luac}) - see tools/ui/README.md build step"
        )

    stop_game_server()

    if args.file:
        rebuild_single(pak, luac, args.file)
    else:
        rebuild_batch(pak, luac)


if __name__ == "__main__":
    main()
