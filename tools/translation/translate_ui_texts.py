"""Translates ui_texts (+ later localized_texts) into Spanish.

Workflow:
  1. Ensures a WORKING COPY of the plaintext compact.sqlite3 at
     .client_files/client-src/<ver>/work/compact.sqlite3 (server original untouched).
  2. Exports pending rows to CSV checkpoint (resumable).
  3. Translates ko -> es in small batches with retries.
  4. Applies results to the working DB (UPDATE ui_texts SET text=<es>).

Usage: python translate_ui_texts.py [--limit N]
"""
import csv
import os
import shutil
import sqlite3
import sys
import time

from deep_translator import GoogleTranslator

ROOT = r"C:\Users\ivang\Desktop\Dev\ArcheaAge"
VER = "1.2"
SRC_DB = os.path.join(ROOT, r"servers\aaemu\AAEmu.Game\Data\compact.sqlite3")
WORK_DIR = os.path.join(ROOT, rf".client_files\client-src\{VER}\work")
WORK_DB = os.path.join(WORK_DIR, "compact.sqlite3")
CSV_PATH = os.path.join(ROOT, rf".client_files\client-src\{VER}\translation\ui_texts.ko.csv")

GLOSSARY = {
    "아이템": "objeto",
    "artículo": "objeto",
    "artículos": "objetos",
    "노동력": "Mano de Obra",
    "escasez de mano de obra": "No tienes suficiente Mano de Obra",
}


def apply_glossary(text: str) -> str:
    for k, v in GLOSSARY.items():
        text = text.replace(k, v)
    return text


def main() -> int:
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0

    os.makedirs(WORK_DIR, exist_ok=True)
    if not os.path.exists(WORK_DB):
        shutil.copyfile(SRC_DB, WORK_DB)
        print("copia de trabajo creada")

    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8-sig")))
    pending = [r for r in rows if not r.get("es")]
    if limit:
        pending = pending[:limit]
    total_pending = len(pending)
    print(f"pendientes: {total_pending}")
    if not total_pending:
        return 0

    tr = GoogleTranslator(source="ko", target="es")
    done = 0
    t0 = time.time()
    batch, batch_rows = [], []

    def flush():
        nonlocal done
        if not batch_rows:
            return
        # write results to CSV checkpoint
        es_by_key = dict(batch)
        for r in rows:
            if r["key"] in es_by_key and not r["es"]:
                r["es"] = es_by_key[r["key"]]
        with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["id", "key", "ko", "es", "category_id"])
            w.writeheader()
            w.writerows(rows)

        conn = sqlite3.connect(WORK_DB)
        for key, es in batch:
            conn.execute("UPDATE ui_texts SET text=? WHERE key=?", (es, key))
        conn.commit()
        conn.close()
        done += len(batch_rows)
        rate = done / max(1e-9, time.time() - t0)
        eta = (total_pending - done) / max(1e-9, rate) / 60
        print(f"  {done}/{total_pending} aplicadas ({rate:.1f}/s, ETA {eta:.0f} min)", flush=True)
        batch.clear()
        batch_rows.clear()

    for r in pending:
        text = r["ko"]
        es = None
        for attempt in range(4):
            try:
                es = tr.translate(text)
                break
            except Exception as e:
                wait = 5 * (attempt + 1)
                print(f"  retry {attempt+1}: {str(e)[:60]} (espero {wait}s)", flush=True)
                time.sleep(wait)
        if es:
            batch.append((r["key"], apply_glossary(es)))
            batch_rows.append(r)
        if len(batch_rows) >= 25:
            flush()
        time.sleep(0.15)
    flush()

    print(f"COMPLETADO: {done} traducidas y aplicadas a {WORK_DB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
