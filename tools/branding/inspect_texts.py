import sqlite3, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB = r".client_files\ArcheAge 1.2 (r208022) for AAEmu\compact.sqlite3"
con = sqlite3.connect(DB)
cur = con.cursor()

cols = [c[1] for c in cur.execute("PRAGMA table_info(localized_texts)")]
print("cols:", cols)
n = cur.execute("SELECT COUNT(*) FROM localized_texts").fetchone()[0]
print("rows:", n)

print("\n--- 'Select Server' rows ---")
for row in cur.execute(
    "SELECT rowid, id, tbl_name, tbl_column_name, idx, en_us FROM localized_texts "
    "WHERE en_us LIKE '%Select Server%' LIMIT 10"
):
    print(row)

print("\n--- 'create up' rows ---")
for row in cur.execute(
    "SELECT rowid, id, tbl_name, tbl_column_name, idx, en_us FROM localized_texts "
    "WHERE en_us LIKE '%create up%' LIMIT 10"
):
    print(row)
