// pak-scan — lists and extracts entries from an ArcheAge game_pak (AAPack).
//
// Usage: dotnet run --project tools/pak-scan -- <game_pak> <outDir> [nameFilter]
//   nameFilter is a case-insensitive substring match on the entry path.
// Extracted files keep their in-pak relative paths under <outDir>.
//
// This is the seed of the future pack/unpack tooling (aapatcher): reading is
// streamed straight from the pak file, no full-archive temp copies.

using AAEmu.Commons.Utils.AAPak;

if (args.Length < 2)
{
    Console.WriteLine("usage: pak-scan <game_pak> <outDir> [nameFilter]");
    return 1;
}

var pakPath = args[0];
var outDir = args[1];
var filter = args.Length > 2 ? args[2] : null;

var pak = new AAPak(pakPath, openAsReadOnly: true);
try
{
    var matches = pak.pakFiles.Values
        .Where(f => filter is null ||
                    f.name.Contains(filter, StringComparison.OrdinalIgnoreCase))
        .OrderBy(f => f.name, StringComparer.OrdinalIgnoreCase)
        .ToList();

    Console.WriteLine($"entries total: {pak.pakFiles.Count}, matching '{filter}': {matches.Count}");

    foreach (var f in matches.Take(50))
        Console.WriteLine($"  {f.name} ({f.size} bytes)");

    if (args.Length > 2)
    {
        foreach (var f in matches)
        {
            var target = Path.Combine(outDir, f.name.Replace('\\', '/'));
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            using var src = pak.ExportFileAsStream(f.name);
            using var dst = File.Create(target);
            src.CopyTo(dst);
        }
        Console.WriteLine($"extracted {matches.Count} file(s) to {outDir}");
    }
}
finally
{
    pak.ClosePak();
}
return 0;
