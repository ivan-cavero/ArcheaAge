#!/usr/bin/env python3
"""dbtext.py — quick CLI edits for a client's localized UI texts (compact.sqlite3).

The ArcheAge client keeps its visible UI strings in compact.sqlite3,
table `localized_texts` (columns: tbl_name, tbl_column_name, idx, ko, en_us, ...).
This tool searches and edits them without opening a GUI.

Usage:
  python tools/db/dbtext.py find "Select Server"          # search en_us
  python tools/db/dbtext.py get 48420                     # dump one row
  python tools/db/dbtext.py set 48420 "New text"          # edit en_us (+backup)
  python tools/db/dbtext.py hash                          # current sha256
  python tools/db/dbtext.py manifest 1.2                  # sync hash into content/manifests/<v>.json

After editing compact.sqlite3 remember: it is a launcher-managed "direct"
file — run `manifest <version>` so Verify/download hashes stay consistent.
"""
import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_DB = Path(".client_files/ArcheAge 1.2 (r208022) for AAEmu/compact.sqlite3")
LANGS = ["ko", "en_us", "zh_cn", "ja", "ru", "zh_tw", "de", "fr"]


def connect(db: Path) -> sqlite3.Connection:
    if not db.exists():
        sys.exit(f"ERROR: db not found: {db}")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con


def backup(db: Path) -> Path:
    b = db.with_suffix(f".{date.today():%Y%m%d}.bak")
    if not b.exists():
        shutil.copy2(db, b)
    return b


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB, help="path to compact.sqlite3")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("find")
    p.add_argument("pattern")
    p.add_argument("--lang", default="en_us", choices=LANGS)
    p.add_argument("-n", type=int, default=25)

    p = sub.add_parser("get")
    p.add_argument("rowid", type=int)

    p = sub.add_parser("set")
    p.add_argument("rowid", type=int)
    p.add_argument("text")
    p.add_argument("--lang", default="en_us", choices=LANGS)

    sub.add_parser("hash")

    p = sub.add_parser("manifest")
    p.add_argument("version")
    p.add_argument("--manifests", type=Path, default=Path("content/manifests"))

    a = ap.parse_args()

    if a.cmd == "hash":
        print(sha256(a.db))
        return

    if a.cmd == "manifest":
        mf = a.manifests / f"{a.version}.json"
        data = json.loads(mf.read_text(encoding="utf-8"))
        for f in data.get("files", []):
            if f.get("name") == "compact.sqlite3":
                old = f.get("sha256")
                f["sha256"] = sha256(a.db)
                mf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"{mf}: {old} -> {f['sha256']}")
                return
        sys.exit("compact.sqlite3 not found among direct files in manifest")
        return

    con = connect(a.db)
    cur = con.cursor()

    if a.cmd == "find":
        q = (
            f"SELECT rowid, tbl_name, idx, {a.lang} AS text FROM localized_texts "
            f"WHERE {a.lang} LIKE ? ORDER BY rowid LIMIT ?"
        )
        for r in cur.execute(q, (f"%{a.pattern}%", a.n)):
            print(f"{r['rowid']:>7}  {r['tbl_name']:<14} idx={r['idx']:<6} {r['text']!r}")

    elif a.cmd == "get":
        r = cur.execute("SELECT * FROM localized_texts WHERE rowid=?", (a.rowid,)).fetchone()
        if not r:
            sys.exit("rowid not found")
        for k in r.keys():
            v = r[k]
            if isinstance(v, str) and len(v) > 90:
                v = v[:90] + "…"
            print(f"{k:>16}: {v}")

    elif a.cmd == "set":
        b = backup(a.db)
        cur.execute(
            f"UPDATE localized_texts SET {a.lang}=? WHERE rowid=?", (a.text, a.rowid)
        )
        if cur.rowcount != 1:
            sys.exit("rowid not found")
        con.commit()
        print(f"ok ({cur.rowcount} row) · backup: {b.name}")
        print("new sha256:", sha256(a.db))
        print("run `python tools/db/dbtext.py manifest <version>` to sync the launcher manifest")


if __name__ == "__main__":
    main()
