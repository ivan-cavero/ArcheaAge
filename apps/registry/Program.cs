using System.Collections.Concurrent;
using System.Text.Json;
using System.Text.Json.Serialization;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<RegistryStore>();

// The launcher's frontend runs from the Vite dev origin and from the Tauri
// WebView2 origin (tauri://localhost, http/https://tauri.localhost). Allow
// those — and localhost — so the renderer can query the registry.
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy
            .SetIsOriginAllowed(origin =>
                origin.StartsWith("http://localhost", StringComparison.OrdinalIgnoreCase) ||
                origin.StartsWith("http://127.0.0.1", StringComparison.OrdinalIgnoreCase) ||
                origin.EndsWith("://tauri.localhost", StringComparison.OrdinalIgnoreCase) ||
                origin.Equals("tauri://localhost", StringComparison.OrdinalIgnoreCase))
            .AllowAnyHeader()
            .AllowAnyMethod();
    });
});

var app = builder.Build();
app.UseCors();

// --- Public reads (the launcher queries these) ---

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

app.MapGet("/news", (RegistryStore store) => Results.Ok(store.News()));

// --- Writes (Game servers report state) ---

app.MapPost("/heartbeat", (Heartbeat body, RegistryStore store) =>
{
    if (!store.IsValidToken(body.Version, body.Token))
        return Results.Unauthorized();
    store.Heartbeat(body);
    return Results.Ok();
});

// Demo: fake servers with fluctuating players for UI development.
// ponytail: dev-only; disable in production (Demo=false).
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

/// <summary>In-memory Registry state.</summary>
public sealed class RegistryStore(IConfiguration config)
{
    private readonly ConcurrentDictionary<string, ServerInfo> _servers = new();

    public string ManifestDir { get; } = FindContentDir();

    // Walk up from the build output until we find the repo's content/ dir —
    // survives moving this project (e.g. root → apps/registry) without edits.
    private static string FindContentDir()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 10 && dir is not null; i++, dir = dir.Parent!)
        {
            var candidate = Path.Combine(dir.FullName, "content", "manifests");
            if (Directory.Exists(candidate)) return candidate;
        }
        return Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "content", "manifests");
    }

    public IEnumerable<VersionSummary> Versions()
    {
        // Known versions: live in config (or default seed). Each entry may
        // carry a display Name; the seed falls back to "ArcheAge {id}".
        var known = config.GetSection("Versions").GetChildren()
            .Select(c => (Id: c["Id"]!, Name: c["Name"] ?? $"ArcheAge {c["Id"]}"))
            .Concat([(Id: "1.2", Name: "ArcheAge 1.2 (launch era)")])
            .DistinctBy(t => t.Id);

        foreach (var (id, name) in known)
        {
            var servers = _servers.Values.Where(s => s.Version == id).ToList();
            yield return new VersionSummary(
                id,
                name,
                ClientVersion(id),
                servers.Count,
                servers.Sum(s => s.Players),
                Servers(id) is null ? "planned" : "live",
                DownloadSize(id));
        }
    }

    /// <summary>Display version of the client (from the manifest), e.g. "1.2.4.0 (r208022)".</summary>
    public string ClientVersion(string version)
    {
        var path = Path.Combine(ManifestDir, $"{version}.json");
        if (!File.Exists(path)) return "";
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        return doc.RootElement.TryGetProperty("client", out var c) && c.ValueKind == JsonValueKind.String
            ? c.GetString()!
            : "";
    }

    /// <summary>Total bytes to download for a version (sum of manifest file sizes).</summary>
    public long DownloadSize(string version)
    {
        var path = Path.Combine(ManifestDir, $"{version}.json");
        if (!File.Exists(path)) return 0;
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        if (!doc.RootElement.TryGetProperty("files", out var files)) return 0;
        long total = 0;
        foreach (var f in files.EnumerateArray())
            if (f.TryGetProperty("size", out var size) && size.TryGetInt64(out var n))
                total += n;
        return total;
    }

    /// <summary>News feed for the launcher (falls back to an empty feed).</summary>
    public object News()
    {
        var path = Path.Combine(ManifestDir, "..", "news.json");
        if (!File.Exists(path)) return new { items = Array.Empty<object>() };
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        return doc.RootElement.Clone(); // expected shape: { "items": [...] }
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

    // ponytail: in-memory + timeout-based prune; MySQL when there's history/metrics
    private void Prune()
    {
        var cutoff = DateTime.UtcNow.AddSeconds(-60);
        foreach (var (id, s) in _servers)
            if (s.LastHeartbeat < cutoff)
                _servers.TryRemove(id, out _);
    }
}

public sealed record VersionSummary(
    string Id,
    string Name,
    string Client,
    int Servers,
    int PlayersOnline,
    string Status,
    long DownloadSize);

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