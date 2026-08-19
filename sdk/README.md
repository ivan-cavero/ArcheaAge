# ArcheaAge.Sdk

Plugin contract for ArcheaAge servers. **Does not reference AAEmu** — a plugin compiles against this package (NuGet `ArcheaAge.Sdk`) without cloning the server.

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
    }

    public void OnUnload() { }
}
```

## Rules

- The SDK is **pure contract** (interfaces + events). The server-side adapter lives in the fork.
- Semantic versioning; the server loads plugins compatible with its SDK version.
- The loader (`Assembly.LoadFrom` + reflection) is implemented in the fork (M2).

## Dev

```bash
dotnet build sdk
dotnet pack sdk -o artifacts/nuget
```
