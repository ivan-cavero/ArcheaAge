// pak-grep — finds entries in an ArcheAge game_pak (AAPack) whose CONTENT
// contains a string (ASCII or UTF-16LE). Read-only, streams entry by entry.
//
// Usage: dotnet run --project tools/pak-grep -- <game_pak> <needle> [maxEntrySize]
//   maxEntrySize (bytes, optional): skip bigger entries to speed up the scan.

using System.Text;
using AAEmu.Commons.Utils.AAPak;

if (args.Length < 2)
{
    Console.WriteLine("usage: pak-grep <game_pak> <needle> [maxEntrySize]");
    return 1;
}

var pakPath = args[0];
var needle = args[1];
var maxSize = args.Length > 2 ? long.Parse(args[2]) : long.MaxValue;

var ascii = Encoding.ASCII.GetBytes(needle);
var utf16 = Encoding.Unicode.GetBytes(needle);

var pak = new AAPak(pakPath, openAsReadOnly: true);
try
{
    var hits = 0;
    foreach (var f in pak.pakFiles.Values.OrderBy(f => f.name, StringComparer.OrdinalIgnoreCase))
    {
        if (f.size > maxSize)
            continue;
        try
        {
            using var src = pak.ExportFileAsStream(f.name);
            using var ms = new MemoryStream();
            src.CopyTo(ms);
            var b = ms.ToArray();
            if (b.AsSpan().IndexOf(ascii) >= 0 || b.AsSpan().IndexOf(utf16) >= 0)
            {
                hits++;
                Console.WriteLine($"HIT {f.name} ({f.size} bytes)");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"SKIP {f.name}: {ex.Message}");
        }
    }
    Console.WriteLine($"done: {hits} hit(s)");
}
finally
{
    pak.ClosePak();
}
return 0;
