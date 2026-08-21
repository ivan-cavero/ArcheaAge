#!/usr/bin/env bash
# ArcheaAge dev-stack launcher (Git Bash / bash on Windows) — portable.
# Starts: Podman MariaDB (compose, auto-migrations) + Registry + Login + Game.
# No hardcoded user paths: the podman VM IP and the client install dir are
# resolved at runtime and written into the server Config.Local.json files.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVER="$ROOT/servers/aaemu"
MDB_HOST=""

say() { printf "\033[1;36m[dev]\033[0m %s\n" "$*"; }

# --- Locate a compose provider (podman-compose may live outside PATH) ---------
find_compose() {
  if command -v podman-compose >/dev/null 2>&1; then
    return 0
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    return 0
  fi
  # pip --user scripts dir (works on any Windows user profile)
  local scripts; scripts="$(python -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>/dev/null)"
  if [ -n "$scripts" ]; then
    PATH="$PATH:$scripts"
    if command -v podman-compose >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

# --- 1. Podman machine + MariaDB via compose ----------------------------------
if ! podman machine info >/dev/null 2>&1; then
  say "Starting podman machine…"
  podman machine start >/dev/null 2>&1 || true
fi

# Fix stale conmon namespace (common after a podman machine restart): if we
# can't exec into the DB container, reset the namespace and restart it.
if podman ps -a --format "{{.Names}}" | grep -q "^archeaage-mariadb$" \
   && ! podman exec archeaage-mariadb mariadb -u root -e "SELECT 1;" >/dev/null 2>&1; then
  say "Resetting podman namespace (conmon)…"
  podman system migrate 2>/dev/null || true
fi

if podman ps --format "{{.Names}}" | grep -q "^archeaage-mariadb$"; then
  say "MariaDB container already running"
elif podman ps -a --format "{{.Names}}" | grep -q "^archeaage-mariadb$"; then
  say "Starting existing MariaDB container…"
  podman start archeaage-mariadb
elif find_compose && podman compose version >/dev/null 2>&1; then
  say "Starting MariaDB with compose (migrations auto-run on a fresh volume)…"
  (cd "$ROOT" && podman compose up -d)
else
  say "Compose not available — falling back to podman run…"
  podman run -d --name archeaage-mariadb \
    -e MARIADB_ALLOW_EMPTY_ROOT_PASSWORD=yes \
    --network host \
    -v mariadb-data:/var/lib/mysql \
    mariadb:11.4 >/dev/null
fi

# Wait for the DB to accept connections. WSL2 relays the VM's ports to
# 127.0.0.1 (wslrelay.exe), so prefer localhost; fall back to the VM IP.
DB_READY=""
for _ in $(seq 1 30); do
  if podman exec archeaage-mariadb mariadb -u root -e "SELECT 1;" >/dev/null 2>&1; then
    DB_READY=1
    break
  fi
  sleep 2
done
[ -n "$DB_READY" ] || { say "ERROR: MariaDB not reachable"; exit 1; }

VM_IP="$(podman machine ssh "ip -4 addr show eth0 2>/dev/null | awk '/inet /{print \$2}' | cut -d/ -f1" 2>/dev/null | tr -d '\r ')"
if python -c "import socket; socket.create_connection(('127.0.0.1', 3306), 2).close()" 2>/dev/null; then
  MDB_HOST="127.0.0.1"
else
  MDB_HOST="$VM_IP"
fi
say "MariaDB at $MDB_HOST:3306 (container archeaage-mariadb)"

# --- 2. Patch server configs (DB host + client data) --------------------------
# Client install dir: same convention the launcher uses (per-user, portable).
CLIENT_DIR="${LOCALAPPDATA:-$HOME/AppData/Local}/ArcheaAge/clients/1.2/game_pak"
CLIENT_DIR="$(cygpath -m "$CLIENT_DIR" 2>/dev/null || echo "$CLIENT_DIR")"

patch_game() {
  python - "$SERVER/AAEmu.Game/Config.Local.json" "$MDB_HOST" "$CLIENT_DIR" <<'PY'
import json, sys
p, host, client = sys.argv[1], sys.argv[2], sys.argv[3]
c = json.load(open(p))
c["Connections"]["MySQLProvider"]["Host"] = host
c["ClientData"] = {"Sources": [client]}
json.dump(c, open(p, "w"), indent=2)
PY
}
patch_login() {
  python - "$SERVER/AAEmu.Login/Config.Local.json" "$MDB_HOST" <<'PY'
import json, sys
p, host = sys.argv[1], sys.argv[2]
c = json.load(open(p))
c["Connections"]["MySQLProvider"]["Host"] = host
json.dump(c, open(p, "w"), indent=2)
PY
}
patch_game
patch_login
cp "$SERVER/AAEmu.Game/Config.Local.json" "$SERVER/AAEmu.Game/bin/Debug/net10.0/"
cp "$SERVER/AAEmu.Login/Config.Local.json" "$SERVER/AAEmu.Login/bin/Debug/net10.0/"

# --- 3. Registry --------------------------------------------------------------
if ! curl -sf http://localhost:5080/health >/dev/null; then
  say "Starting registry…"
  (cd "$ROOT/apps/registry" && nohup dotnet run --no-build >/tmp/registry.log 2>&1 &)
  sleep 3
fi

# --- 4. Login + Game servers ---------------------------------------------------
is_running() {
  powershell -NoProfile -Command \
    "(Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'AAEmu\.$1\.dll' }).Count -gt 0" 2>/dev/null | tr -d '\r' | grep -qi true
}
start_dotnet() {
  local dir="$1" name="$2"
  if is_running "$name"; then
    say "$name already running"
  else
    say "Starting $name…"
    (cd "$dir" && nohup dotnet "AAEmu.$name.dll" >"/tmp/$name.log" 2>&1 &)
    sleep 3
  fi
}
start_dotnet "$SERVER/AAEmu.Login/bin/Debug/net10.0" "Login"
start_dotnet "$SERVER/AAEmu.Game/bin/Debug/net10.0" "Game"

echo
say "Registry: http://localhost:5080 · Login 1234/1237 · Game 1239 · DB $MDB_HOST:3306"
say "Servers reported by registry:"
curl -s http://localhost:5080/versions/1.2/servers | head -c 200; echo