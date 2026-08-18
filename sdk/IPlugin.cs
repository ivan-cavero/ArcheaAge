namespace ArcheaAge.Sdk;

/// <summary>
/// Contrato de un plugin. El server (fork de AAEmu) carga ensamblados que
/// implementan esta interfaz — el loader se implementa en el fork (workstream M2).
/// </summary>
public interface IAaPlugin
{
    /// <summary>Identificador único estilo DNS inverso: "dev.archeaage.tradepack-tweaks".</summary>
    string Id { get; }

    string Name { get; }

    string Version { get; }

    void OnLoad(IPluginContext context);

    void OnUnload();
}

/// <summary>Contexto inyectado al cargar el plugin.</summary>
public interface IPluginContext
{
    IEventBus Events { get; }

    Microsoft.Extensions.Logging.ILogger Logger { get; }
}

/// <summary>
/// Bus de eventos tipado. El server publica eventos de juego (login, quest,
/// craft, combate...); los plugins se suscriben. El adaptador que traduce los
/// eventos de AAEmu a este bus vive en el fork, no en el SDK.
/// </summary>
public interface IEventBus
{
    void Subscribe<T>(Action<T> handler) where T : GameEvent;

    void Unsubscribe<T>(Action<T> handler) where T : GameEvent;

    void Publish<T>(T evt) where T : GameEvent;
}

public abstract record GameEvent(DateTime OccurredAt);

// --- Eventos de ejemplo (el fork los publicará en sus managers) ---

public sealed record PlayerLoggedIn(long AccountId, long CharacterId, string Name)
    : GameEvent(DateTime.UtcNow);

public sealed record QuestCompleted(long CharacterId, uint QuestId)
    : GameEvent(DateTime.UtcNow);

public sealed record ItemCrafted(long CharacterId, uint ItemTemplateId, int Count)
    : GameEvent(DateTime.UtcNow);