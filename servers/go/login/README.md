# servers/go/login — Slice 1 (not started)

Login server in Go: account auth, server list, and the **1.2 client packet
protocol** (`trino_1_2`, see `docs/VERSIONS.md`).

Scope per [ADR-001](../../docs/ADR/ADR-001-server-language-go.md):

- AES-128-CBC + XOR packet crypto, opcode map for 1.2.
- Auth flow: login → token → server list → enter world handoff to the game
  server.
- Accounts DB (MySQL — same stack as today; migrations will live in
  `db/migrations/`).

Reference implementation while porting: `servers/aaemu/AAEmu.Login`
(C#, read-only reference — do not import).
