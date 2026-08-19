# ArcheaAge.Registry

Metaserver: version list, per-version servers with **live online players** (Game server heartbeats) and client manifests.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Liveness |
| `GET` | `/versions` | Versions + summary |
| `GET` | `/versions/{v}/servers` | Servers for the version |
| `GET` | `/versions/{v}/manifest` | Client manifest (reads `content/manifests/{v}.json`) |
| `POST` | `/heartbeat` | Game → Registry (per-version Bearer token) |

## Config

```jsonc
// appsettings.json
{
  "Tokens": { "1.2": "dev-secret" },
  "Versions": [ { "Id": "1.2" } ],
  "Demo": true   // fake servers with fluctuating players (UI dev)
}
```

## Dev

```bash
dotnet run --project registry
curl http://localhost:5080/versions
```

The manifest is served from `content/manifests/` (relative to the repo). With no servers heartbeating, `/servers` returns an empty list if a manifest exists, 404 otherwise.
