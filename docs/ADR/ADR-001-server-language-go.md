# ADR-001: Rewrite the game server in Go

- **Status**: Accepted
- **Date**: 2026
- **Deciders**: project owner (with this ADR as the record)

---

## Context

The AAEmu game server fork (`server/`) is C#/.NET (~197k LOC, 2.8k+ `.cs` files).
The project owner wants to **rewrite it from scratch** — not as a port, but to
learn the stack properly and redesign the architecture (modules, tick-based
world simulation, concurrency) without inheriting the fork's constraints.

Constraints considered:

- Deployment target is **Linux** (containers). .NET 5+ is fully cross-platform,
  so this was *not* the deciding factor — the rewrite is a learning/design goal,
  not a portability escape.
- Concurrency matters: this is a world-simulation server, not a CRUD API.
- Person of one in the early phase: on-ramp and iteration speed determine whether
  the rewrite finishes.

## Options considered

| Option | Outcome |
| --- | --- |
| Keep C#/.NET (rewrite in place) | Best ecosystem fit (plugins, existing docs), but doesn't serve the "learn and redesign" goal and keeps the .NET learning curve. |
| Node.js/TypeScript | Weak fit: JS GC degrades under a tick-driven world sim (p95 spikes in 10k-player benchmarks). CRUD-friendly, world-sim-hostile. |
| **Go** (chosen) | Best balance of learning curve, concurrency model (goroutines), and throughput. Iteration-per-slice is visible and motivating. |
| Rust | Highest raw ceiling and control, best for the launcher (already Rust). But steepest curve — highest abandonment risk while learning on a whole MMO rewrite. |

## Decision

Write the new login + game servers in **Go**.

- **What is ported** (language-agnostic knowledge, carried over as-is):
  the packet/opcode spec per version, packet structures, Lua content scripts,
  client data handling. The protocol RE work does **not** restart.
- **What is redesigned**: network core, packet decoder/encoder, session dispatch,
  tick-driven world simulation, state sharing / DB policy.
- **What stays**: launcher stays **Rust + Tauri** (already built; Go and Rust
  interoperate via REST). Go serves data the launcher consumes.

## Consequences

- Plugin model changes: no more `Assembly.LoadFrom` + NuGet. Go plugins load as
  dynamic `.so`; Lua kept for content scripts. Event bus first, loading details
  tracked separately (does not block).
- The AAEmu fork becomes a **reference** (protocol/code/opcodes), not the
  production server.

## Slice plan (anti-big-bang)

Every slice leaves something that runs.

1. **Slice 0** — Registry in Go (REST, versions/servers/heartbeat). Small, learns
   the stack for real.
2. **Slice 1** — Login server in Go: auth + server list + 1.2 packet protocol.
3. **Slice 2** — Game network core: packet decoder/encoder, session, opcode
   dispatcher.
4. **Slice 3** — One gameplay module end-to-end (lightest: spawn + movement)
   before porting the rest.
5. **Slice 4+** — Expand to world scope, module by feature slice.

## Consequence / open items

- Registry() is migrated C# → Go as part of Slice 0.
- Avoid the 9-month big bang: never "rewrite everything then turn it on".
