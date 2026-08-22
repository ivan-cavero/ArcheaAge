import hashlib
import shutil
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CLIENT = r".client_files\ArcheAge 1.2 (r208022) for AAEmu"
DB = CLIENT + r"\compact.sqlite3"

BRAND_LINE = "ArcheaAge \u00b7 Edited by Ivan Cavero"

shutil.copy2(DB, DB + ".bak")
print("backup ->", DB + ".bak")

con = sqlite3.connect(DB)
cur = con.cursor()

targets = [
    (1160, "You can create up to 4 characters on any one server and six characters across all servers."),
    (5169, "You can create up to 4 characters on any one server and a total of 6 characters across all servers."),
]
for idx, old in targets:
    cur.execute(
        "UPDATE localized_texts SET en_us = ? WHERE tbl_name='ui_texts' AND idx = ? AND en_us = ?",
        (BRAND_LINE, idx, old),
    )
    print(f"idx {idx}: updated rows =", cur.rowcount)

con.commit()
con.close()

h = hashlib.sha256(open(DB, "rb").read()).hexdigest()
print("new sha256:", h)
