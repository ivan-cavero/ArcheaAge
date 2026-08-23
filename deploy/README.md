# deploy/ — VPS deployment (Garage S3)

Private infra on your VPS, deployed with **Dokploy** (or plain docker compose).

## What you open on the VPS firewall

| Port | Protocol | Purpose |
| --- | --- | --- |
| 22 | TCP | SSH — never close |
| 80 | TCP | HTTP (Traefik cert renewal) |
| 443 | TCP+UDP | HTTPS (all app traffic) |

That's it. Dokploy/Traefik reverse-proxies everything else internally.

## Garage (S3 for artifacts)

S3-compatible object storage for the heavy stuff: base client archives
(~158 GB), paks, releases and backups (restic/rclone). NOT for git.

- **Why Garage and not MinIO**: MinIO entered maintenance mode (Dec 2025)
  and crippled the CE console; Garage is Rust, light, S3-compatible.
- **Self-contained compose**: the garage image has no shell, so a tiny
  alpine init container writes `/etc/garage/garage.toml` from env vars.
  No external files to mount — paste the compose + a `.env` and it works
  under Dokploy.

### Deploy (Dokploy)

1. Create a **Compose** service. Paste `deploy/garage/compose.yaml`.
2. Set the env vars in the service (Environment tab):

   ```
   GARAGE_RPC_SECRET=openssl rand -hex 32
   GARAGE_ADMIN_TOKEN=openssl rand -hex 32
   ```

3. Add a domain, e.g. `s3.169.58.216.96.nip.io` → port `3900` → HTTPS.
4. Deploy.

### First run (layout + bucket + key)

```bash
alias gr="docker exec -it garage /garage -c /etc/garage/garage.toml"
gr status                                  # copy the NODE ID
gr layout assign -z dc1 -c 250GB <NODE_ID> # capacity = real disk size
gr layout apply --version 1
gr bucket create archeaage-artifacts
gr key create archeaage                    # save Key ID + Secret Key!
gr bucket allow --read --write archeaage-artifacts --key archeaage
```

### Upload with rclone

```bash
rclone config   # type s3, provider Other, endpoint https://s3.169.58.216.96.nip.io
rclone copy .clients archeaage:archeaage-artifacts/clients --progress
```

## Persistent data (bind mounts in /var/lib)

- Garage: `/var/lib/garage/meta` + `/var/lib/garage/data` (S3 objects)

Back these up with restic/rclone — they are the only state that matters.

## What goes to Garage (never to git)

- `.clients/` (~158 GB of client archives, multi-volume 7z)
- `.client_files/`, `.server_files/` (extracted client, server data)
- Releases and backups (restic/rclone)
