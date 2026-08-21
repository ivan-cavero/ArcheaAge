# ADR-000: Deployment on Linux; portability of the original stack

- **Status**: Accepted (contextual — informs ADR-001)
- **Date**: 2026

## Context

Concern raised: ".NET forces you onto Windows" — a reason to consider another
language for the server rewrite. This is a misinterpretation that needed
resolving before picking a new stack.

## Facts (researched, 2026)

- .NET Framework (the "classic", `4.x`) was Windows-only — the source of the
  reputation.
- **.NET Core 3.1+ (2017) — now just ".NET", current major 10 — is fully
  cross-platform** (Windows, Linux, macOS). Cross-platform is an official design
  goal.
- Performance is **equivalent or better on Linux** (same AOT-compiled native
  binaries; less OS overhead in server roles).
- The repository already ships Linux deployment: `server/docker-compose.yaml`
  builds `AAEmu.Login` and `AAEmu.Game` via their `Dockerfile`s (Linux
  containers), and `deploy/compose.yaml` already runs MariaDB via podman/docker.

## Consequence

Portability to Linux is **not** a reason to change language. The rewrite to Go
(ADR-001) is motivated by a learning + redesign goal, not by any Windows
lock-in. All four candidate stacks deploy on Linux equally well.
