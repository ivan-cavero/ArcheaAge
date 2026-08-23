#!/usr/bin/env python3
"""sync_tree.py — copies the freshly generated game UI tree from
Documents\\ArcheAge into the Studio's static frontend so it auto-loads,
then validates it is parseable JSON.

Regeneration flow (per client version):
  1. tools/ui/push_ui.py            (injects probe_dump.alb)
  2. Play until server-select, close
  3. python tools/ui/sync_tree.py
  4. commit apps/studio/ui/game_ui_tree.json
"""
import json
import os
import shutil
import sys

SRC = os.path.join(
    os.environ.get("USERPROFILE", os.path.expanduser("~")),
    "Documents", "ArcheAge", "game_ui_tree.json",
)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DST = os.path.join(REPO_ROOT, "apps", "studio", "ui", "game_ui_tree.json")


def main() -> int:
    if not os.path.isfile(SRC):
        print(
            f"tree not found: {SRC} "
            "(run one in-game pass with the probe injected)",
            file=sys.stderr,
        )
        return 1

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    shutil.copyfile(SRC, DST)

    try:
        with open(DST, encoding="utf-8") as f:
            json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"copied file is not valid JSON: {e}", file=sys.stderr)
        return 1

    with open(DST, encoding="utf-8") as f:
        nodes = f.read().count('"path"')
    print(f"synced + valid JSON \u00b7 {nodes} nodes -> {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
