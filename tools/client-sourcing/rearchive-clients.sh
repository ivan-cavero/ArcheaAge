#!/usr/bin/env bash
# Re-comprime los clientes descargados en 7z multi-volumen (partes).
# Para cada *.7z/*.zip en .clients (no toca .exe):
#   1. extrae a un staging temporal
#   2. re-comprime en partes de 2 GB (mx=7, mejor ratio)
#   3. solo entonces borra el original y el staging
# Resume-safe: salta los que ya tienen <base>.7z.001.
#
# Uso: bash tools/client-sourcing/rearchive-clients.sh [substring-filtro]
# PART_SIZE=4g bash tools/client-sourcing/rearchive-clients.sh   (tamaño de parte configurable)
set -uo pipefail

SEVEN="C:/Program Files/7-Zip/7z.exe"
CLIENTS="$(cd "$(dirname "$0")/.." && pwd)/.clients"
LOG="$CLIENTS/rearchive.log"
PART="${PART_SIZE:-2g}"
ONLY="${1:-}"
mkdir -p "$CLIENTS"

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

find "$CLIENTS" -type f \( -name '*.7z' -o -name '*.zip' \) -print0 |
  while IFS= read -r -d '' ARC; do
    name="$(basename "$ARC")"
    dir="$(dirname "$ARC")"
    base="${ARC%.*}"
    [ -n "$ONLY" ] && ! printf '%s' "$ARC" | grep -q "$ONLY" && continue
    ls "$base".7z.001 >/dev/null 2>&1 && {
      log "SKIP (ya en partes): $name"
      continue
    }

    STAGE="$dir/.stage_$(basename "$base")"
    log "==> [1/3] extrayendo: $name"
    rm -rf "$STAGE"
    mkdir -p "$STAGE"
    "$SEVEN" x "$ARC" -o"$STAGE" -y >>"$LOG" 2>&1 ||
      {
        log "ERROR extrayendo $name (original conservado)"
        rm -rf "$STAGE"
        continue
      }

    log "==> [2/3] recomprimiendo: $name -> partes de $PART"
    TMPO="${base}.new" # nombre temporal: no colisiona con el original
    (cd "$STAGE" && "$SEVEN" a -t7z -mx=7 -v"$PART" "$TMPO.7z" .) >>"$LOG" 2>&1 ||
      {
        log "ERROR comprimiendo $name (original conservado)"
        rm -rf "$STAGE"
        continue
      }
    ls "$TMPO".7z.001 >/dev/null 2>&1 ||
      {
        log "ERROR: sin partes para $name"
        rm -rf "$STAGE"
        continue
      }

    # renombra los .new.7z.XXX a la base original (para no dejar el .new colgando)
    for p in "$TMPO".7z.*; do mv "$p" "$(printf '%s' "$p" | sed 's/\.new\.7z/.7z/')"; done

    log "==> [3/3] borrando original + staging: $name"
    rm -f "$ARC"
    rm -rf "$STAGE"
    n=$(ls -d "$base".7z.* 2>/dev/null | wc -l)
    log "OK  $name -> $(basename "$base").7z.001..$n ($n partes)"
    df -h "$CLIENTS" | tail -1 | tee -a "$LOG"
  done
log "=== TERMINADO ==="
