#!/usr/bin/env bash
# Stops the ArcheaAge dev stack (keeps the Podman MariaDB container data volume).
set -euo pipefail

kill_if() {
  local pattern="$1"
  powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -like '*$pattern*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }" 2>/dev/null || true
}

kill_if "AAEmu.Game.dll"
kill_if "AAEmu.Login.dll"
kill_if "ArcheaAge.Registry"

echo "[dev] Stopped Login, Game and Registry (MariaDB container left running)."
echo "[dev] To also stop the DB: podman stop aaemu-mariadb"