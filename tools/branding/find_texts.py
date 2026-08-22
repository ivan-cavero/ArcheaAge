import sqlite3, sys

DB = r".client_files\ArcheAge 1.2 (r208022) for AAEmu\compact.sqlite3"
con = sqlite3.connect(DB)
cur = con.cursor()

tabs = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("tables:", len(tabs))
cand = [t for t in tabs if any(k in t.lower() for k in ("str", "text", "local", "lang", "ui"))]
print("candidates:", cand[:20])
for t in cand[:8]:
    cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})")]
    n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t} rows={n} cols={cols}")

# locate the exact rows carrying the visible texts
for t in tabs:
    cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})")]
    textcols = [c for c, ty in ((c[1], c[2]) for c in cur.execute(f"PRAGMA table_info({t})")) if "TEXT" in ty.upper() or "CHAR" in ty.upper()]
    if not textcols:
        continue
    for col in textcols:
        q = f'SELECT rowid, {col} FROM {t} WHERE {col} LIKE ? LIMIT 5'
        try:
            for rid, val in cur.execute(q, ("%Select Server%",)):
                print(f"HIT {t}.{col} rowid={rid}: {val!r}")
        except Exception:
            pass
