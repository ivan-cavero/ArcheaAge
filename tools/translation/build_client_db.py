"""Builds the CLIENT compact.sqlite3 by applying translation CSVs.

Usage:
  python build_client_db.py <base_db> <csv_dir> <out_db>

  <base_db>  plaintext source db (e.g. servers/aaemu/AAEmu.Game/Data/compact.sqlite3)
  <csv_dir>  folder with translated CSVs (content/i18n/es/<ver>/)
             - ui_texts.csv            cols: id,key,ko,es,category_id
             - localized_texts.*.csv   cols: id,tbl_name,tbl_column_name,idx,en_us,es
  <out_db>   resulting client deliverable (plain sqlite)

Only rows whose `es` is non-empty are applied.
"""
import csv
import glob
import os
import shutil
import sqlite3
import sys


def apply_ui(conn, csv_path):
    n = 0
    with open(csv_path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("es"):
                conn.execute("UPDATE ui_texts SET text=? WHERE id=?", (r["es"], r["id"]))
                n += 1
    return n


def apply_localized(conn, csv_path):
    n = 0
    with open(csv_path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if not r.get("es"):
                continue
            # Strategy A: overwrite en_us so any `-lang en_us` shows Spanish.
            conn.execute(
                "UPDATE localized_texts SET en_us=?, en_us_ver=en_us_ver+1 "
                "WHERE tbl_name=? AND tbl_column_name=? AND idx=?",
                (r["es"], r["tbl_name"], r["tbl_column_name"], r["idx"]),
            )
            n += 1
    return n


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        return 1
    base, csv_dir, out = sys.argv[1:4]
    shutil.copyfile(base, out)
    conn = sqlite3.connect(out)
    total = 0
    for path in sorted(glob.glob(os.path.join(csv_dir, "*.csv"))):
        name = os.path.basename(path).lower()
        n = apply_ui(conn, path) if name.startswith("ui_texts") else apply_localized(conn, path)
        print(f"{os.path.basename(path)}: {n} aplicadas")
        total += n
    conn.commit()
    conn.close()
    print(f"OK {out}: {total} traducciones aplicadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
