import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB = r".client_files\ArcheAge 1.2 (r208022) for AAEmu\compact.sqlite3"
con = sqlite3.connect(DB)
cur = con.cursor()

needles = ["loginstage", "world_select", "x2ui"]
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("tables:", len(tables))
for t in tables:
    try:
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})")]
    except Exception:
        continue
    for col in cols:
        for ndl in needles:
            try:
                n = cur.execute(
                    f"SELECT COUNT(*) FROM {t} WHERE {col} LIKE ?", (f"%{ndl}%",)
                ).fetchone()[0]
                if n:
                    print(f"HIT {t}.{col} ~ '{ndl}': {n} filas")
                    for row in cur.execute(
                        f"SELECT * FROM {t} WHERE {col} LIKE ? LIMIT 3", (f"%{ndl}%",)
                    ):
                        s = str(row)[:200]
                        print("   ", s)
            except Exception:
                pass
