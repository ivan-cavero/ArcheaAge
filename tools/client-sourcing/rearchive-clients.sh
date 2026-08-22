#!/usr/bin/env bash
# Re-packs the downloaded clients into multi-volume (split) 7z archives.
# For each *.7z/*.zip in .clients (.exe files untouched):
#   1. extract to a temporary staging folder
#   2. re-compress into 2 GB parts (mx=7, best ratio)
#   3. only then delete the original and the staging folder
# Resume-safe: skips the ones that already have <base>.7z.001.
#
# Usage: bash tools/client-sourcing/rearchive-clients.sh [substring-filter]
# PART_SIZE=4g bash tools/client-sourcing/rearchive-clients.sh   (configurable part size)
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
      log "SKIP (already split): $name"
      continue
    }

    STAGE="$dir/.stage_$(basename "$base")"
    log "==> [1/3] extracting: $name"
    rm -rf "$STAGE"
    mkdir -p "$STAGE"
    "$SEVEN" x "$ARC" -o"$STAGE" -y >>"$LOG" 2>&1 ||
      {
        log "ERROR extracting $name (original kept)"
        rm -rf "$STAGE"
        continue
      }

    log "==> [2/3] re-compressing: $name -> parts of $PART"
    TMPO="${base}.new" # temp name: does not collide with the original
    (cd "$STAGE" && "$SEVEN" a -t7z -mx=7 -v"$PART" "$TMPO.7z" .) >>"$LOG" 2>&1 ||
      {
        log "ERROR compressing $name (original kept)"
        rm -rf "$STAGE"
        continue
      }
    ls "$TMPO".7z.001 >/dev/null 2>&1 ||
      {
        log "ERROR: no parts produced for $name"
        rm -rf "$STAGE"
        continue
      }

    # rename the .new.7z.XXX parts back to the original base (no .new left hanging)
    for p in "$TMPO".7z.*; do mv "$p" "$(printf '%s' "$p" | sed 's/\.new\.7z/.7z/')"; done

    log "==> [3/3] deleting original + staging: $name"
    rm -f "$ARC"
    rm -rf "$STAGE"
    n=$(ls -d "$base".7z.* 2>/dev/null | wc -l)
    log "OK  $name -> $(basename "$base").7z.001..$n ($n parts)"
    df -h "$CLIENTS" | tail -1 | tee -a "$LOG"
  done
log "=== DONE ==="
