// client-sync — extracts the "source" of a game_pak into a git-friendly tree.
//
// Usage: dotnet run --project tools/client-sync -- <game_pak> <outDir>
//
// Extracts every entry whose extension looks editable (lua/alb/xml/cfg/txt/
// json/csv/sql/ini/htm/html/js/css/rb) plus game/db/compact.sqlite3 (all game
// texts live there). Binary assets (models/textures/sounds) stay in the pak;
// pull them individually with pak-scan when needed.
//
// Point your LOCAL git at <outDir> to track every change you make. Never push
// game assets to a public repository (see docs/LEGAL.md).

using AAEmu.Commons.Utils.AAPak;

if (args.Length != 2)
{
    Console.WriteLine("usage: client-sync <game_pak> <outDir>");
    return 1;
}

var pakPath = args[0];
var outRoot = Path.GetFullPath(args[1]);

var textExt = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    ".lua", ".alb", ".xml", ".cfg", ".txt", ".json", ".csv", ".sql",
    ".ini", ".htm", ".html", ".js", ".css", ".rb", ".ent", ".loc",
};

var pak = new AAPak(pakPath, openAsReadOnly: true);
try
{
    var done = 0;
    var bytes = 0L;
    foreach (var f in pak.pakFiles.Values.OrderBy(f => f.name, StringComparer.OrdinalIgnoreCase))
    {
        var norm = f.name.Replace('\\', '/');
        var ext = Path.GetExtension(norm);
        var isDb = norm.Equals("game/db/compact.sqlite3", StringComparison.OrdinalIgnoreCase);
        if (!isDb && !textExt.Contains(ext))
            continue;

        var target = Path.Combine(outRoot, norm);
        Directory.CreateDirectory(Path.GetDirectoryName(target)!);
        using var src = pak.ExportFileAsStream(f.name);
        using var dst = File.Create(target);
        src.CopyTo(dst);
        done++;
        bytes += f.size;
    }
    Console.WriteLine($"extracted {done} file(s), {bytes / 1048576.0:N1} MB -> {outRoot}");
}
finally
{
    pak.ClosePak();
}
return 0;
