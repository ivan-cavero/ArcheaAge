# servers/go/game — Slices 2+ (not started)

Game server in Go: network core first, then world simulation module by
feature slice.

Scope per [ADR-001](../../docs/ADR/ADR-001-server-language-go.md):

- **Slice 2** — network core: packet decoder/encoder, sessions, opcode
  dispatcher.
- **Slice 3** — one gameplay module end-to-end (spawn + movement) before
  porting anything else.
- **Slice 4+** — expand to world scope; tick-driven simulation; plugin event
  bus (Go plugins + Lua content scripts).

Reference implementation while porting: `servers/aaemu/AAEmu.Game`
(C#, read-only reference — do not import).
