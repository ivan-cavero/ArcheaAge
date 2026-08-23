# deploy/ — VPS deployment (Forgejo + Garage)

Private infra on your VPS, deployed with **Dokploy** (or plain docker compose).

## What you open on the VPS firewall

| Port | Protocol | Purpose |
| --- | --- | --- |
| 22 | TCP | SSH — never close |
| 80 | TCP | HTTP (Traefik cert renewal) |
| 443 | TCP+UDP | HTTPS (all app traffic) |

That's it. Dokploy/Traefik reverse-proxies everything else internally; you
never expose 3000, 3900, or the Forgejo port directly.

## Forgejo (git)

1. Create a **Compose** service in Dokploy, set a domain
   (e.g. `git.yourdomain.com`) pointed at `http://forgejo:3000`.
2. Paste `deploy/forgejo/compose.yaml`, upload `.env` with:

   ```
   FORGEJO_DOMAIN=git.yourdomain.com
   ```

3. First admin user:

   ```
   docker exec -it <ctr> gitea admin user create --admin \
     --username ivan --email you@mail --password XXX
   ```

   Then disable public registration in the UI.

## Garage (S3 for artifacts)

1. Copy `garage.toml.example` → `garage.toml` next to the compose file.
2. Create a **Compose** service in Dokploy. Paste `deploy/garage/compose.yaml`,
   upload `garage.toml` and `.env` with:

   ```
   GARAGE_RPC_SECRET=openssl rand -hex 32
   GARAGE_ADMIN_TOKEN=openssl rand -hex 32
   ```

   (Garage reads these env vars instead of secrets in the toml.)
3. First run (layout + bucket + key):

   ```
   alias gr="docker exec -it garage /garage"
   gr layout show                       # copy the NODE ID
   gr layout assign -z dc1 -c 1 <NODE_ID>
   gr layout apply
   gr bucket create archeaage-artifacts
   gr key create archeaage
   gr bucket allow --read --write archeaage-artifacts --key archeaage
   ```

## What goes to Garage (never to git)

- `.clients/` (~158 GB of client archives, multi-volume 7z)
- `.client_files/`, `.server_files/` (extracted client, server data)
- Releases and backups (restic/rclone)

## Git remote

```bash
git remote add forgejo https://git.yourdomain.com/ivan/ArcheaAge.git
git push forgejo main
```
