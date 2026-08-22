// pak-put — writes/adds a single file into an ArcheAge game_pak (AAPack).
//
// Usage: dotnet run --project tools/pak-put -- <game_pak> <local_file> <as_pak_path>
//   Replaces the entry if it already exists, otherwise adds it as new.
//   The FAT/header is saved and the written entry is verified by MD5.
//
// WARNING: modifies the pak in place. Keep the original archive around
// (the distribution .zip/.7z) as your restore path.

using AAEmu.Commons.Utils.AAPak;

if (args.Length != 3)
{
    Console.WriteLine("usage: pak-put <game_pak> <local_file> <as_pak_path>");
    return 1;
}

var pakPath = args[0];
var localFile = args[1];
var asPath = args[2].Replace('\\', '/').ToLowerInvariant();

if (!File.Exists(localFile))
{
    Console.WriteLine($"ERROR: local file not found: {localFile}");
    return 1;
}

// Fail fast with a clear message if the pak is locked (client running).
try
{
    using var lockProbe = new FileStream(pakPath, FileMode.Open, FileAccess.ReadWrite, FileShare.None);
}
catch (IOException ex)
{
    Console.WriteLine($"ERROR: game_pak is locked (is the client running?). {ex.Message}");
    return 1;
}

var pak = new AAPak(pakPath, openAsReadOnly: false);
if (pak.pakFiles.Count == 0)
{
    Console.WriteLine("ERROR: pak opened but file table is empty (locked, corrupt header, or wrong file).");
    return 1;
}
Console.WriteLine($"pak open: {pak.pakFiles.Count} entries");
try
{
    var modified = DateTime.Now;

    // Locate the entry by enumerating (GetFileByName/FileExists use an exact
    // internal key lookup that misses case/separator variants).
    var pair = pak.pakFiles
        .FirstOrDefault(kv => kv.Value.name.Replace('\\', '/').Equals(asPath, StringComparison.OrdinalIgnoreCase));

    if (!default(KeyValuePair<string, AAPakFileInfo>).Equals(pair) && pair.Value.name.Length > 0)
    {
        Console.WriteLine($"found stored key: '{pair.Key}'");
        var info = pair.Value;
        using var src = File.OpenRead(localFile);
        if (!pak.ReplaceFile(ref info, src, modified))
        {
            Console.WriteLine("ERROR: ReplaceFile failed");
            return 1;
        }
        Console.WriteLine($"replaced: {info.name} ({info.size} bytes)");
    }
    else
    {
        // Show near-matches to diagnose path/case mismatches.
        foreach (var kv in pak.pakFiles.Values)
            if (kv.name.Replace('\\', '/').EndsWith("client.cfg", StringComparison.OrdinalIgnoreCase))
                Console.WriteLine($"existing similar: '{kv.name}'");
        if (!pak.AddFileFromFile(localFile, asPath, autoSpareSpace: true))
        {
            Console.WriteLine("ERROR: AddFileFromFile failed");
            return 1;
        }
        Console.WriteLine($"added: {asPath}");
    }

    pak.SaveHeader();

    // Verify: reopen the entry and compare MD5 with the local file.
    pak.ClosePak();
    var verify = new AAPak(pakPath, openAsReadOnly: true);
    try
    {
        var vpair = verify.pakFiles.FirstOrDefault(kv =>
            kv.Value.name.Replace('\\', '/').Equals(asPath, StringComparison.OrdinalIgnoreCase));
        if (vpair.Value.name.Length > 0)
        {
            var md5 = BitConverter.ToString(vpair.Value.md5).Replace("-", "").ToLowerInvariant();
            var localMd5 = Convert.ToHexString(
                System.Security.Cryptography.MD5.HashData(File.ReadAllBytes(localFile))
            ).Replace("-", "").ToLowerInvariant();
            Console.WriteLine(md5 == localMd5
                ? $"VERIFIED ok (md5 {md5})"
                : $"WARNING md5 mismatch! pak={md5} local={localMd5}");
        }
        else
        {
            Console.WriteLine("WARNING: entry not found after write!");
        }
    }
    finally
    {
        verify.ClosePak();
    }
}
catch (Exception ex)
{
    Console.WriteLine($"ERROR: {ex.Message}");
    return 1;
}
return 0;
