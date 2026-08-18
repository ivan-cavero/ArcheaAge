# ArcheaAge.Sdk

Contrato de plugins para servidores ArcheaAge. **No referencia AAEmu** — un plugin se compila contra este paquete (NuGet `ArcheaAge.Sdk`) sin clonar el server.

```csharp
public sealed class MyPlugin : IAaPlugin
{
    public string Id => "dev.archeaage.my-plugin";
    public string Name => "My Plugin";
    public string Version => "1.0.0";

    public void OnLoad(IPluginContext ctx)
    {
        ctx.Events.Subscribe<PlayerLoggedIn>(e =>
            ctx.Logger.LogInformation("Bienvenido {Name}!", e.Name));
    }

    public void OnUnload() { }
}
```

## Reglas

- El SDK es **contrato puro** (interfaces + eventos). El adaptador server-side vive en el fork.
- Versionado semántico; el server carga plugins compatibles con su versión de SDK.
- El loader (`Assembly.LoadFrom` + reflexión) se implementa en el fork (M2).

## Dev

```bash
dotnet build sdk
dotnet pack sdk -o artifacts/nuget
```
