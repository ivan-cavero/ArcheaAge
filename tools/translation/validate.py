"""Validates translation CSVs: length vs English reference + duplicates.

Usage:
  python validate.py <csv_dir>

Rules:
  - localized_texts.*.csv : warn if len(es) > len(en_us) * 1.15
  - ui_texts.csv          : warn if len(es) > len(ko) * 1.6  (KO is denser)
  - warns on empty es, and on identical es for different keys that look
    like copy-paste mistakes (same text >3 times).
Outputs a warnings report to stdout; exit code 0 always (advisory).
"""
import csv
import glob
import os
import sys


def main():
    csv_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    warnings = 0
    for path in sorted(glob.glob(os.path.join(csv_dir, "*.csv"))):
        name = os.path.basename(path)
        is_ui = name.lower().startswith("ui_texts")
        seen = {}
        with open(path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                es = r.get("es", "")
                key = r.get("key") or f"{r.get('tbl_name')}.{r.get('tbl_column_name')}.{r.get('idx')}"
                if not es:
                    print(f"[EMPTY ] {name}:{key}")
                    warnings += 1
                    continue
                ref = r.get("en_us") or r.get("ko") or ""
                factor = 1.15 if "en_us" in r else 1.6
                if ref and len(es) > len(ref) * factor:
                    print(f"[LONG  ] {name}:{key} es={len(es)} ref={len(ref)}")
                    warnings += 1
                seen.setdefault(es, []).append(key)
        for es, keys in seen.items():
            if len(keys) > 3:
                print(f"[DUP   ] {name}: '{es[:40]}' repetido {len(keys)} veces")
                warnings += 1
    print(f"total avisos: {warnings}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
