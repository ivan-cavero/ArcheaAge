# Contributing to ArcheaAge

Thanks for your interest! This is an open-source private-server project:
a multi-version launcher, a metaserver, community plugins and custom content
around the AAEmu emulator family. All code here is LGPL-3.0 (see `LICENSE`).

## Code of conduct

Be excellent to each other. Keep criticism technical, welcome newcomers.

## Repository map

| Path | What lives there |
| --- | --- |
| `apps/registry/` | Metaserver (C#/ASP.NET Core): versions, live servers, manifests, news |
| `apps/launcher/` | Tauri v2 launcher (Rust + web): version picker, server browser, client manager |
| `servers/aaemu/` | AAEmu fork (**git submodule** → `ivan-cavero/AAEmu`, branch `archeaage/develop`) |
| `servers/go/` | Go rewrite of the servers (ADR-001): registry (Slice 0), login, game |
| `sdk/` | Plugin contract (`ArcheaAge.Sdk`) — compiles without cloning the server |
| `plugins/` | Community plugin catalog (one folder per plugin) |
| `content/` | Client manifests per version + launcher news feed + content packs |
| `tools/` | Client sourcing, packing, opcode/RE utilities, editors (future) |
| `db/migrations/` | Our own SQL migrations (forward-only) |
| `scripts/` | Dev ops: start-dev, stop-dev, upload-client, write-aelcf |
| `docs/` | Research, architecture, spec, ADRs, version table |

## Prerequisites

| Component | Used by | Version |
| --- | --- | --- |
| .NET SDK | registry, sdk, plugins | 10.0 |
| Go | servers/go | 1.25+ |
| Rust + Node | apps/launcher | stable / LTS |
| Podman or Docker | dev DB (compose.yaml) | any recent |

## Build & test

```bash
# .NET side (registry + sdk + plugins)
dotnet build ArcheaAge.slnx
dotnet test  ArcheaAge.slnx --no-build

# Go side
cd servers/go && go vet ./... && go test ./...

# Launcher
cd apps/launcher && npm install && npm run tauri dev

# Dev stack (MariaDB + everything)
bash scripts/start-dev.sh      # stop with scripts/stop-dev.sh
```

CI runs the .NET build/tests, `cargo check` for the launcher and Go vet/test
on every push and PR — keep it green.

## How we work

### Branches & commits

- `main` is the integration branch; keep it releasable.
- Conventional Commits are required: `feat:`, `fix:`, `chore:`, `docs:`,
  `ci:`, `refactor:`, `test:` — optionally scoped (`feat(launcher): ...`).
- One logical change per commit; rebase before opening a PR when possible.

### Server work (AAEmu fork)

The fork lives at [ivan-cavero/AAEmu](https://github.com/ivan-cavero/AAEmu)
(branch `archeaage/develop`). Upstream is kept as a remote to stay in sync:

```bash
git submodule update --init servers/aaemu
cd servers/aaemu
git remote -v   # origin = our fork, upstream = AAEmu/AAEmu
```

Follow the upstream contributing rules inside the submodule (conventional
commits, tests where applicable).

### Plugins

1. Read `sdk/IPlugin.cs` — the contract is intentionally tiny.
2. Add `plugins/<YourPlugin>/` referencing only the SDK (never the server).
3. Include unit tests; a plugin PR without tests does not land.
4. CI compiles every catalog plugin against each release (compatibility
   matrix) — your plugin must keep compiling.

### Content packs

Anything that touches the client travels as a **versioned content pack** via
the launcher manifest system:

```bash
bash scripts/upload-client.sh <version> <client-dir> <login-type>
```

Never commit client assets — see the disclaimer below.

## Legal notes (please read)

- **No game assets in this repo.** The ArcheAge client, `game_pak`,
  `compact.sqlite3`, art, music and trademarks are property of **XLGAMES**
  (and/or its publishers). Local working copies live in gitignored folders
  (`.clients/`, `.client_files/`).
- Server code derives from AAEmu (LGPL-3.0); our own code is LGPL-3.0 too.
- Reverse engineering done under this project targets interoperability for
  private, educational and preservation purposes.

## Where to discuss

Open a GitHub Issue or Discussion on this repository. For server-emulator
internals, the AAEmu Discord is the reference community.
