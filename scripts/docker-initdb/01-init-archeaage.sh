#!/usr/bin/env bash
# Auto-migration for the ArcheaAge MariaDB container.
# Runs once by the mariadb image entrypoint on a fresh data volume:
# creates the game/login databases, imports the schemas and seeds the test user.
set -e
echo "[archeaage-init] creating databases…"
mariadb -u root -e \
  "CREATE DATABASE IF NOT EXISTS aaemu_game CHARACTER SET utf8mb4; \
   CREATE DATABASE IF NOT EXISTS aaemu_login CHARACTER SET utf8mb4;"

echo "[archeaage-init] importing aaemu_game schema…"
mariadb -u root aaemu_game < /sql-src/aaemu_game.sql

echo "[archeaage-init] importing aaemu_login schema…"
mariadb -u root aaemu_login < /sql-src/aaemu_login.sql

echo "[archeaage-init] seeding test user (test)…"
mariadb -u root aaemu_login < /sql-src/examples/test-user.sql

echo "[archeaage-init] migrations done."
