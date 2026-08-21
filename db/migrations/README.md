# db/ — ArcheaAge database migrations

SQL that **we** own as a project. Two clearly separated worlds:

| Path | Owner | Notes |
| --- | --- | --- |
| `servers/aaemu/SQL/` | AAEmu fork (upstream structure) | `aaemu_game.sql`, `aaemu_login.sql` + `updates/`. Applied automatically on a fresh volume by `compose.yaml` → `scripts/docker-initdb/`. |
| `db/migrations/` | **ArcheaAge (ours)** | Schema changes for *our* services: registry persistence (when it moves from in-memory to MySQL), account site, metrics/history, cross-server features. |

## Conventions

- Forward-only: never edit an applied migration — add a new one.
- Naming: `YYYY-MM-DD_<service>_<description>.sql`
  (e.g. `2026-09-01_registry_heartbeats.sql`).
- Every migration must be idempotent-safe to run once and re-runnable in CI
  against a scratch database (`IF NOT EXISTS`, no bare `CREATE DATABASE`).
- One logical change per file; pair schema + seed data in the same file.

## Applying

- Dev: the MariaDB container applies `servers/aaemu/SQL` on first start.
  For our own migrations, apply manually for now:
  `podman exec -i archeaage-mariadb mariadb -u root <db> < db/migrations/<file>.sql`.
- When the Go registry gains MySQL persistence (ADR-001 Slice 0 follow-up),
  we adopt [`golang-migrate`](https://github.com/golang-migrate/migrate) and
  this folder becomes its source of truth.
