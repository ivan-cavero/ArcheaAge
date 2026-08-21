# .client_files/ — local extracted client (NEVER committed)

This folder holds an **extracted ArcheAge client** on your machine only.
Everything here is ignored by git (except this README) because:

1. **Legal**: the client and its assets are property of XLGAMES — they are
   never redistributed through this repository or its releases.
2. **Size**: a full install is multiple GB.

## Who reads it

- `servers/aaemu/AAEmu.Game` — `ClientData.Sources` in `Config.Local.json`
  points here (e.g. `<repo>/.client_files/1.2/game_pak`) so the game server
  can read game data without owning a copy.
- Tools under `tools/` that inspect `game_pak`, opcodes, or client Lua.

## How to populate it

1. Get the client archives into `.clients/` (see `docs/VERSIONS.md` for the
   official sources) — those are the multi-volume `.7z/.zip` files.
2. Extract per version, one subfolder each:

   ```bash
   # example: 1.2
   7z x ".clients/<client-1.2>.7z.001" -o.client_files/1.2
   ```

3. Point the server at it — `scripts/start-dev.sh` does this automatically
   when the launcher-style layout exists; otherwise edit
   `servers/aaemu/AAEmu.Game/Config.Local.json` → `ClientData.Sources`.

Related: `.clients/` (raw archives, also gitignored) and
`scripts/upload-client.sh` (publishes a client folder to S3 + generates the
launcher manifest in `content/manifests/`).
