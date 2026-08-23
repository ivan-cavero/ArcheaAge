#!/usr/bin/env python3
"""push.py — one-shot UI iteration for our client-side Lua addon.

Port of push-ui.ps1 + install-ui-addon.ps1 to Python.

  python tools/ui/push.py                 # compile + inject (default)
  python tools/ui/push.py install-addon   # inject addon as plain Lua source

Steps (default):
  1. compiles tools/ui/addon_panel.lua -> luac-build/addon_panel.alb
     (luac5f.exe = Lua 5.1 built with LUA_NUMBER=float — REQUIRED, see README)
     overrides.lua from the visual editor is prepended when present.
  2. compiles tools/ui/probe_dump.lua -> luac-build/probe_dump.alb
  3. injects into the CLIENT game_pak:
       - the compiled addon   -> game/scriptsbin/x2ui/loginstage/addon_panel.alb
       - probe_dump.alb       -> game/scriptsbin/x2ui/loginstage/probe_dump.alb
       - both toc.g hooks     -> .../loginstage/login/toc.g and .../world_select/toc.g
         (idempotent: pak-put replaces existing entries)

Player-side iteration = edit .lua -> run this -> reopen the game (~1 min).
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
UI_DIR = Path(__file__).resolve().parent


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


def compile_lua(luac, src, out):
    run([luac, "-o", out, src], "compile")


def pak_put(pak, local, entry):
    project = REPO_ROOT / "tools" / "pak-put"
    run(
        ["dotnet", "run", "--project", project, "--", pak, local, entry],
        f"pak-put for {entry}",
    )


def push(pak, luac):
    if not pak.exists():
        raise RuntimeError(f"game_pak not found: {pak}")
    if not luac.exists():
        raise RuntimeError(
            f"luac5f.exe not found ({luac}) - see tools/ui/README.md build step"
        )

    # 1. compile (overrides.lua from the visual editor is prepended when present)
    src = UI_DIR / "addon_panel.lua"
    ovr = UI_DIR / "overrides.lua"
    probe_src = UI_DIR / "probe_dump.lua"
    alb = UI_DIR / "luac-build" / "addon_panel.alb"
    alb2 = UI_DIR / "luac-build" / "probe_dump.alb"

    if ovr.exists():
        combined = Path(tempfile.gettempdir()) / "aa_ui_combined.lua"
        combined.write_text(
            ovr.read_text(encoding="utf-8") + "\n" + src.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        compile_lua(luac, combined, alb)
    else:
        compile_lua(luac, src, alb)
    compile_lua(luac, probe_src, alb2)
    print(f"[1/2] compiled: {alb.stat().st_size} bytes")

    # 2. inject (idempotent)
    pairs = [
        (alb, "game/scriptsbin/x2ui/loginstage/addon_panel.alb"),
        (alb2, "game/scriptsbin/x2ui/loginstage/probe_dump.alb"),
        (UI_DIR / "login_toc.g", "game/scriptsbin/x2ui/loginstage/login/toc.g"),
        (
            UI_DIR / "world_select_toc.g",
            "game/scriptsbin/x2ui/loginstage/world_select/toc.g",
        ),
    ]
    for local, entry in pairs:
        pak_put(pak, local, entry)
    print("[2/2] injected. Reopen the game client to see changes.")


def install_addon(pak):
    """install-ui-addon.ps1: inject addon as plain Lua SOURCE (no compile)."""
    if not pak.exists():
        raise RuntimeError(f"game_pak not found: {pak}")
    pairs = [
        (UI_DIR / "addon_panel.lua", "game/scriptsbin/x2ui/addon_panel.lua"),
        (UI_DIR / "login_toc.g", "game/scriptsbin/x2ui/loginstage/login/toc.g"),
    ]
    for local, entry in pairs:
        pak_put(pak, local, entry)
    print("UI addon installed.")


def main():
    parser = argparse.ArgumentParser(
        description="Push our Lua UI addon into the client game_pak"
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="push",
        choices=["push", "install-addon"],
        help="push (default): compile+inject; install-addon: inject Lua source",
    )
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

    if args.action == "install-addon":
        install_addon(pak)
    else:
        push(pak, luac)


if __name__ == "__main__":
    main()
