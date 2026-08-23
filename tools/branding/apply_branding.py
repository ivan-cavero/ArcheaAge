#!/usr/bin/env python3
"""apply_branding.py — replaces the login-stage "made by" page inside an
ArcheAge client game_pak with our own branding (whole-file swap via pak-put,
so there is no length limit and the original stays recoverable from the
distribution archives in .clients/).

Usage:
  python tools/branding/apply_branding.py apply --client-dir "<dir with game_pak>" \
      [--line1 "ArcheaAge"] [--line2 "Edited by Ivan Cavero"]

Re-run any time to change the text; re-apply to a fresh client copy before
re-archiving it for distribution (tools/client-sourcing/rearchive-clients.sh).
"""
import argparse
import os
import subprocess
import sys
import tempfile

BRANDING_HTML = """<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>made</title>
<style>
  html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
  #brand {{
    position: absolute; left: 0; right: 0; bottom: 28px; text-align: center;
    font-family: "Trebuchet MS", Verdana, sans-serif; color: #cfe3ff;
    text-shadow: 0 0 6px rgba(80, 140, 255, 0.9), 0 1px 2px #000;
  }}
  #brand .l1 {{ font-size: 22px; font-weight: bold; letter-spacing: 5px; }}
  #brand .l2 {{ font-size: 13px; letter-spacing: 2px; margin-top: 7px; color: #9fb8d8; }}
</style>
</head>
<body valign="middle" leftmargin="0" topmargin="0">
<div id="brand">
  <div class="l1">{line1}</div>
  <div class="l2">{line2}</div>
</div>
</body>
</html>
"""

ENTRIES = (
    "game/ui/login_stage/html/made_en.html",
    "game/ui/login_stage/html/made_kr.html",
)


def repo_root() -> str:
    # tools/branding/apply_branding.py -> repo root (3 levels up)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pak_put(pak: str, local: str, entry: str) -> None:
    cmd = [
        "dotnet", "run", "--project",
        os.path.join(repo_root(), "tools", "pak-put"),
        "--", pak, local, entry,
    ]
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise SystemExit(f"pak-put failed for {entry}")


def cmd_apply(args: argparse.Namespace) -> int:
    pak = os.path.join(args.client_dir, "game_pak")
    if not os.path.isfile(pak):
        raise SystemExit(f"game_pak not found: {pak}")

    html = BRANDING_HTML.format(line1=args.line1, line2=args.line2)
    tmp_dir = tempfile.mkdtemp(prefix="aa-branding")
    dst = os.path.join(tmp_dir, "made_branded.html")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    for entry in ENTRIES:
        pak_put(pak, dst, entry)

    print(f"branding applied: '{args.line1}' / '{args.line2}'")
    print(
        "restore path: re-extract game_pak from the original archive in .clients/"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replace the login-stage 'made by' page in a client game_pak"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    apply = sub.add_parser("apply", help="apply branding to a client game_pak")
    apply.add_argument("--client-dir", required=True, help="dir containing game_pak")
    apply.add_argument("--line1", default="ArcheaAge")
    apply.add_argument("--line2", default="Edited by Ivan Cavero")
    apply.set_defaults(func=cmd_apply)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
