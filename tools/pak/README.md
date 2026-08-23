# tools/pak — Python access to ArcheAge game_pak (AAPack)

Read-only Python library for the ArcheAge `game_pak` (AAPack format).
Byte-identical extraction to AAEmu's C# `AAPak` (`tools/pak-scan` / `pak-put`).

## Dependency

```bash
pip install pycryptodome
```

## API

```python
from tools.pak import open_pak

pak = open_pak("path/to/game_pak")

pak.list_entries()                          # [(name, size), ...] all entries
pak.list_entries("levelinfo")               # case-insensitive substring filter
pak.file_size("game/.../levelinfo.xml")     # int | None
pak.extract("game/.../levelinfo.xml", "out.xml")   # bool
pak.extract_prefix("game/worlds/", "outdir")       # int (count extracted)
for chunk in pak.stream("game/.../big.chr"):       # chunked read (1 MiB)
    ...
```

Never extracts the whole pak — the FAT is read from the tail, file payloads
are read with `seek` on demand.

## Format (read path)

- Trailing 0x200 header, AES-128-CBC (key = XLGamesKey, IV = zeros), identifies
  pak type (`WIBO`/`IDEJ`/`ZERO`) and file counts.
- FAT right before the header, aligned to 0x200; each entry is 0x150 bytes,
  independently AES-CBC encrypted: name(0x108) + offset + size + md5 + times.
- Payloads stored raw at (offset, size) — no decryption.

## Validation

```bash
# same file via C# and Python, compare bytes:
dotnet run --project tools/pak-scan -- <pak> /tmp/cs levelinfo
python3 -c "from tools.pak import open_pak; open_pak('<pak>').extract('game/worlds/arche_mall_world/cells/003_003/client/levelinfo.xml','/tmp/py.xml')"
cmp /tmp/cs/game/worlds/arche_mall_world/cells/003_003/client/levelinfo.xml /tmp/py.xml
```

Verified byte-identical on 187 B and 391 KB files; 218,074 entries parsed
(matches pak-scan's count).
