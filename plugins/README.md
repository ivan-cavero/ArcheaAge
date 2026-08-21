# Plugins

> **Status: transitional.** Community plugins will ultimately target the Go
> server (**Go plugins + Lua content scripts**, per
> [ADR-001](../docs/ADR/ADR-001-server-language-go.md)). This catalog and
> the C# `ArcheaAge.Sdk` are the fork-era scaffold; nothing loads plugins
> yet. See [`../sdk/README.md`](../sdk/README.md).

Community plugin catalog for ArcheaAge. Each plugin:

1. References `ArcheaAge.Sdk` (NuGet) — does not clone the server.
2. Implements `IAaPlugin` (Id, Name, Version, OnLoad/OnUnload).
3. Subscribes to bus events (`PlayerLoggedIn`, `QuestCompleted`, `ItemCrafted`, ...).
4. Ships its own tests (CI runs them against each SDK release — compatibility matrix).

## Catalog entry rules

- Open source code (LGPLv3 or compatible).
- Green build + tests in CI.
- No access to player data outside the SDK contract.
- Changes that touch the client (zones, models, UI) ship as **content packs** in `../content/`, not in the plugin.

## Example

```bash
dotnet build plugins/Example
```

Structure reference: `Example/ExamplePlugin.cs`.
