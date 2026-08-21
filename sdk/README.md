# ArcheaAge.Sdk

> **Status: transitional.** The long-term plugin model is **Go plugins +
> Lua content scripts** ([ADR-001](../docs/ADR/ADR-001-server-language-go.md)).
> This C# contract belongs to the current AAEmu-fork era and to the earlier
> plan; no plugin loader exists yet on any server. It is kept as (a) the
> design reference for the event-bus model that the Go API will follow and
> (b) a working scaffold for C#-side tooling during the transition. Expect
> it to be retired when the Go plugin API lands.

## What an "SDK" is here

A tiny contract package that lets someone **write a plugin without cloning
the server**: it defines what a plugin looks like (`IAaPlugin`) and which
game events it can listen to (`IEventBus`, `PlayerLoggedIn`,
`QuestCompleted`, …). The server publishes those events; plugins subscribe.
The SDK **does not reference AAEmu** — a plugin compiles against this
package alone.

```csharp
public sealed class MyPlugin : IAaPlugin
{
    public string Id => "dev.archeaage.my-plugin";
    public string Name => "My Plugin";
    public string Version => "1.0.0";

    public void OnLoad(IPluginContext ctx)
    {
        ctx.Events.Subscribe<PlayerLoggedIn>(e =>
            ctx.Logger.LogInformation("Welcome {Name}!", e.Name));
        ctx.Events.Subscribe<ItemCrafted>(e => /* ... */);
    }

    public void OnUnload() { }
}
```

## Rules

- The SDK is **pure contract** (interfaces + events). The server-side adapter lives in the fork.
- Semantic versioning; the server loads plugins compatible with its SDK version.
- The loader (`Assembly.LoadFrom` + reflection) was planned for the fork (M2)
  but has **not been built**; see ADR-001 for where plugin loading is going.

## Dev

```bash
dotnet build sdk
dotnet pack sdk -o artifacts/nuget
```
