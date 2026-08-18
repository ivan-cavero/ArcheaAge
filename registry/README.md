# ArcheaAge.Registry

Metaserver: lista de versiones, servidores por versión con **jugadores online en vivo** (heartbeat de los Game servers) y manifiestos de client.

## Endpoints

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/health` | Liveness |
| `GET` | `/versions` | Versiones + resumen |
| `GET` | `/versions/{v}/servers` | Servers de la versión |
| `GET` | `/versions/{v}/manifest` | Manifiesto del client (lee `content/manifests/{v}.json`) |
| `POST` | `/heartbeat` | Game → Registry (Bearer token por versión) |

## Config

```jsonc
// appsettings.json
{
  "Tokens": { "1.2": "dev-secret" },
  "Versions": [ { "Id": "1.2" } ],
  "Demo": true   // servidores ficticios con players fluctuantes (dev de la UI)
}
```

## Dev

```bash
dotnet run --project registry
curl http://localhost:5080/versions
```

El manifiesto se sirve desde `content/manifests/` (relativo al repo). Sin servidores heartbeateando, `/servers` devuelve lista vacía si existe manifiesto, 404 si no.
