using System.Collections.Concurrent;
using System.Text.Json;
using System.Text.Json.Serialization;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<RegistryStore>();
var app = builder.Build();

// --- Lectura pública (el launcher consulta esto) ---

app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

app.MapGet("/versions", (RegistryStore store) =>
    Results.Ok(new { versions = store.Versions() }));

app.MapGet("/versions/{version}/servers", (string version, RegistryStore store) =>
{
    var servers = store.Servers(version);
    return servers is null ? Results.NotFound() : Results.Ok(new { servers });
});

app.MapGet("/versions/{version}/manifest", (string version, RegistryStore store) =>
{
    var manifest = store.Manifest(version);
    return manifest is null ? Results.NotFound() : Results.Ok(manifest);
});

// --- Escritura (los Game servers reportan estado) ---

app.MapPost("/heartbeat", (Heartbeat body, RegistryStore store) =>
{
    if (!store.IsValidToken(body.Version, body.Token))
        return Results.Unauthorized();
    store.Heartbeat(body);
    return Results.Ok();
});

// Demo: servidores ficticios con players fluctuantes para desarrollo de la UI.
// ponytail: solo para dev; desactivar en producción (Demo=false).
if (app.Configuration.GetValue<bool>("Demo"))
{
    _ = Task.Run(async () =>
    {
        var rnd = new Random();
        var store = app.Services.GetRequiredService<RegistryStore>();
        while (true)
        {
            foreach (var (id, name) in new[] { ("eu-1", "ArcheaAge EU-1"), ("na-1", "ArcheaAge NA-1") })
                store.Heartbeat(new Heartbeat("dev-secret", "1.2", id, name,
                    "online", rnd.Next(40, 220), 500));
            await Task.Delay(10000);
        }
    });
}

app.Run();

// ---------------------------------------------------------------------------

/// <summary>Estado en memoria del Registry.</summary>
public sealed class RegistryStore(IConfiguration config)
{
    private readonly ConcurrentDictionary<string, ServerInfo> _servers = new();

    public string ManifestDir { get; } =
        Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "content", "manifests");

    public IEnumerable<VersionSummary> Versions()
    {
        // Versiones conocidas: viven en la config (o seed por defecto).
        var known = config.GetSection("Versions").GetChildren()
            .Select(c => c["Id"]!)
            .Concat(["1.2"]) // seed por defecto para dev
            .Distinct();

        foreach (var id in known)
        {
            var servers = _servers.Values.Where(s => s.Version == id).ToList();
            yield return new VersionSummary(
                id,
                servers.Count,
                servers.Sum(s => s.Players),
                Servers(id) is null ? "planned" : "live");
        }
    }

    public List<ServerInfo>? Servers(string version)
    {
        var servers = _servers.Values.Where(s => s.Version == version).ToList();
        return servers.Count == 0 && !HasManifest(version) ? null : servers;
    }

    public object? Manifest(string version)
    {
        var path = Path.Combine(ManifestDir, $"{version}.json");
        return File.Exists(path) ? JsonSerializer.Deserialize<object>(File.ReadAllText(path)) : null;
    }

    public bool IsValidToken(string version, string token) =>
        !string.IsNullOrEmpty(token) &&
        token == config[$"Tokens:{version}"];

    public void Heartbeat(Heartbeat h)
    {
        _servers[h.ServerId] = new ServerInfo(
            h.ServerId, h.ServerName, h.Version, h.Status, h.Players, h.MaxPlayers,
            DateTime.UtcNow);
        Prune();
    }

    private bool HasManifest(string version) =>
        File.Exists(Path.Combine(ManifestDir, $"{version}.json"));

    // ponytail: in-memory + prune por timeout; MySQL cuando haya historial/métricas
    private void Prune()
    {
        var cutoff = DateTime.UtcNow.AddSeconds(-60);
        foreach (var (id, s) in _servers)
            if (s.LastHeartbeat < cutoff)
                _servers.TryRemove(id, out _);
    }
}

public sealed record VersionSummary(string Id, int Servers, int PlayersOnline, string Status);

public sealed record ServerInfo(
    string Id,
    string Name,
    string Version,
    string Status,
    int Players,
    int MaxPlayers,
    DateTime LastHeartbeat);

public sealed record Heartbeat(
    string Token,
    string Version,
    string ServerId,
    string ServerName,
    string Status,
    int Players,
    int MaxPlayers);