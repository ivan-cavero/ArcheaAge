# tools/pak — Python access to ArcheAge game_pak (AAPack)

Read-only Python library for the ArcheAge `game_pak` (AAPack format).
Byte-identical extraction to AAEmu's C# `AAPak` (the writer is still
`tools/pak-put`). One file handle stays open
for sequential reads (bake / extract / grep) so the archive is not reopened
per file.

**Write/replace** still uses `dotnet run --project tools/pak-put`.

## Dependency

```bash
pip install -r tools/requirements.txt
```

## CLI

```bash
python -m tools.pak scan    <pak> [filter]
python -m tools.pak extract <pak> <outDir> [filter]
python -m tools.pak grep    <pak> <needle> [maxEntrySize]
```

## API

```python
from tools.pak import open_pak, PakIndex

with open_pak("path/to/game_pak") as pak:
    pak.list_entries()                          # [(name, size), ...]
    pak.list_entries("levelinfo")               # case-insensitive substring
    pak.read("game/.../levelinfo.xml")          # bytes | None (case-insensitive)
    pak.extract("game/.../levelinfo.xml", "out.xml")
    pak.extract_matching("outdir", "levelinfo") # substring filter
    pak.extract_prefix("game/worlds/", "outdir")
    idx = PakIndex(pak)                         # facade used by tools.world
    raw = idx.read("game/worlds/main_world/cells/010_012/client/terrain/heightmap.dat")
```

Never extracts the whole pak — the FAT is read from the tail, file payloads
are read with `seek` on demand. Not thread-safe (shared seek pointer).

## Format (read path)

- Trailing 0x200 header, AES-128-CBC (key = XLGamesKey, IV = zeros), identifies
  pak type (`WIBO`/`IDEJ`/`ZERO`) and file counts.
- FAT right before the header, aligned to 0x200; each entry is 0x150 bytes,
  independently AES-CBC encrypted: name(0x108) + offset + size + md5 + times.
- Payloads stored raw at (offset, size) — no decryption.

## Validation

```bash
python -m tools.pak extract <pak> /tmp/py levelinfo
# 218,074 entries parsed; payloads are raw (no decrypt) at (offset, size).
```

Verified byte-identical on 187 B and 391 KB files; 218,074 entries parsed.
