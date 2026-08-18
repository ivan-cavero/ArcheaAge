using ArcheaAge.Sdk;
using Microsoft.Extensions.Logging;

namespace ArcheaAge.Plugins.Example;

/// <summary>
/// Plugin de ejemplo: loguea eventos del bus y muestra el patrón de suscripción.
/// Los plugins se cargan en el server (fork de AAEmu) — el loader llega en M2.
/// </summary>
public sealed class ExamplePlugin : IAaPlugin
{
    public string Id => "dev.archeaage.example";
    public string Name => "Example Plugin";
    public string Version => "0.1.0";

    public void OnLoad(IPluginContext context)
    {
        context.Logger.LogInformation("Plugin {Id} v{Version} cargado.", Id, Version);

        context.Events.Subscribe<PlayerLoggedIn>(e =>
            context.Logger.LogInformation("👋 {Name} ha entrado al mundo.", e.Name));

        context.Events.Subscribe<QuestCompleted>(e =>
            context.Logger.LogInformation("Quest {QuestId} completada por {CharacterId}.", e.QuestId, e.CharacterId));
    }

    public void OnUnload()
    {
    }
}