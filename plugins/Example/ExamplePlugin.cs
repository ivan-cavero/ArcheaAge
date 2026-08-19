using ArcheaAge.Sdk;
using Microsoft.Extensions.Logging;

namespace ArcheaAge.Plugins.Example;

/// <summary>
/// Example plugin: logs bus events and shows the subscription pattern.
/// Plugins are loaded in the server (AAEmu fork) — the loader lands in M2.
/// </summary>
public sealed class ExamplePlugin : IAaPlugin
{
    public string Id => "dev.archeaage.example";
    public string Name => "Example Plugin";
    public string Version => "0.1.0";

    public void OnLoad(IPluginContext context)
    {
        context.Logger.LogInformation("Plugin {Id} v{Version} loaded.", Id, Version);

        context.Events.Subscribe<PlayerLoggedIn>(e =>
            context.Logger.LogInformation("👋 {Name} entered the world.", e.Name));

        context.Events.Subscribe<QuestCompleted>(e =>
            context.Logger.LogInformation("Quest {QuestId} completed by {CharacterId}.", e.QuestId, e.CharacterId));
    }

    public void OnUnload()
    {
    }
}
