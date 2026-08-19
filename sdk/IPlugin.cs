namespace ArcheaAge.Sdk;

/// <summary>
/// Plugin contract. The server (AAEmu fork) loads assemblies implementing
/// this interface — the loader lives in the fork (workstream M2).
/// </summary>
public interface IAaPlugin
{
    /// <summary>Unique DNS-style identifier: "dev.archeaage.tradepack-tweaks".</summary>
    string Id { get; }

    string Name { get; }

    string Version { get; }

    void OnLoad(IPluginContext context);

    void OnUnload();
}

/// <summary>Context injected when the plugin is loaded.</summary>
public interface IPluginContext
{
    IEventBus Events { get; }

    Microsoft.Extensions.Logging.ILogger Logger { get; }
}

/// <summary>
/// Typed event bus. The server publishes game events (login, quest,
/// craft, combat...); plugins subscribe. The adapter translating AAEmu
/// events to this bus lives in the fork, not in the SDK.
/// </summary>
public interface IEventBus
{
    void Subscribe<T>(Action<T> handler) where T : GameEvent;

    void Unsubscribe<T>(Action<T> handler) where T : GameEvent;

    void Publish<T>(T evt) where T : GameEvent;
}

public abstract record GameEvent(DateTime OccurredAt);

// --- Example events (the fork will publish them from its managers) ---

public sealed record PlayerLoggedIn(long AccountId, long CharacterId, string Name)
    : GameEvent(DateTime.UtcNow);

public sealed record QuestCompleted(long CharacterId, uint QuestId)
    : GameEvent(DateTime.UtcNow);

public sealed record ItemCrafted(long CharacterId, uint ItemTemplateId, int Count)
    : GameEvent(DateTime.UtcNow);