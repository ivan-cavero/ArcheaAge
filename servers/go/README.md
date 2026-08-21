# servers/go — the ArcheaAge server rewrite in Go

Per [ADR-001](../../docs/ADR/ADR-001-server-language-go.md) the production
login + game servers are being rewritten in Go, slice by slice. The AAEmu fork
(`servers/aaemu`) stays as the protocol/data reference and the production
server during the transition (M1–M2).

## Layout

| Path | Status | Slice | What it is |
| --- | --- | --- | --- |
| `registry/` | **working** | Slice 0 | Metaserver: versions, live servers, heartbeats, manifests, news. Drop-in replacement for `apps/registry` (same endpoints, same JSON shapes). |
| `login/` | scaffold | Slice 1 | Login server: auth + server list + the 1.2 packet protocol. |
| `game/` | scaffold | Slice 2+ | Game network core (packet codec, session dispatch) and tick-driven world simulation. |

## Run the registry

```bash
cd servers/go
go run ./registry            # listens on :5080
# GET http://localhost:5080/versions
```

The registry auto-discovers the repo's `content/` directory (manifests +
news). Configuration via environment:

| Variable | Default | Meaning |
| --- | --- | --- |
| `REGISTRY_ADDR` | `:5080` | Listen address |
| `REGISTRY_TOKEN_1_2` (etc.) | `dev-secret` | Heartbeat token per version |
| `REGISTRY_DEMO` | `0` | Fake EU/NA servers with fluctuating players (UI dev) |

## Test

```bash
go test ./...
go vet ./...
```

CI runs both on every push/PR (see `.github/workflows/ci.yml`, job `go`).
