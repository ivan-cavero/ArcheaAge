#!/usr/bin/env python3
"""paklib.py — read-only Python library for ArcheAge game_pak (AAPack).

Byte-identical extraction to AAEmu's C# AAPak (tools/pak-scan / pak-put).
Format reverse-engineered from servers/aaemu/AAEmu.Commons/Utils/AAPak/AAPak.cs.

Format (read path):
  - The pak ends with a 0x200 (512) byte header, AES-128-CBC encrypted
    (key = XLGamesKey, IV = 16 zero bytes, no padding).
    Decrypted header identifies the pak type and file counts:
      TypeA: b"WIBO" at 0,   fileCount at +8,  extraFileCount at +12
      TypeB: b"IDEJ" at +8,  fileCount at +12, extraFileCount at +0
      TypeF: b"ZERO" at 0,   fileCount at +8,  extraFileCount at +12
  - The FAT (file table) sits right before the header, aligned to 0x200.
    Each entry is 0x150 (336) bytes, independently AES-CBC encrypted
    (same key/IV), containing name + offset + size + md5 + timestamps.
  - File payloads are stored raw at (offset, size) — no decryption.

Requires: pycryptodome  (pip install pycryptodome)
"""

from __future__ import annotations

import struct
from collections.abc import Iterator
from pathlib import Path

from Crypto.Cipher import AES

XLGAMES_KEY = bytes.fromhex("321F2AEEAA584AB49A6C9E09D59E9C6F")
HEADER_SIZE = 0x200
FILE_INFO_SIZE = 0x150

# name(0x108) offset(8) size(8) sizeDuplicate(8) paddingSize(4)
# md5(16) dummy1(4) createTime(8) modifyTime(8) dummy2(8) = 0x150
_TYPE_A_STRUCT = struct.Struct("<264s qqq i 16s I q q Q")
_TYPE_B_STRUCT = struct.Struct("<i 16s I q 264s q q q q Q")
_TYPE_F_STRUCT = struct.Struct("<Q 264s q q q i 16s I q q")


class PakEntry:
    __slots__ = (
        "name",
        "offset",
        "size",
        "size_duplicate",
        "padding_size",
        "md5",
        "dummy1",
        "create_time",
        "modify_time",
        "dummy2",
    )

    def __init__(
        self,
        name: str,
        offset: int,
        size: int,
        size_duplicate: int,
        padding_size: int,
        md5: bytes,
        dummy1: int,
        create_time: int,
        modify_time: int,
        dummy2: int,
    ):
        self.name = name
        self.offset = offset
        self.size = size
        self.size_duplicate = size_duplicate
        self.padding_size = padding_size
        self.md5 = md5
        self.dummy1 = dummy1
        self.create_time = create_time
        self.modify_time = modify_time
        self.dummy2 = dummy2

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"PakEntry(name={self.name!r}, offset={self.offset}, size={self.size})"


def _decrypt(data: bytes, key: bytes = XLGAMES_KEY) -> bytes:
    """AES-128-CBC decrypt, IV = 16 zero bytes, no padding (mirrors C#)."""
    return AES.new(key, AES.MODE_CBC, iv=b"\x00" * 16).decrypt(data)


def _parse_name(raw: bytes) -> str:
    """C-string: up to first NUL, latin-1 (byte-preserving)."""
    return raw.split(b"\x00", 1)[0].decode("latin-1")


def _parse_entry(block: bytes, pak_type: str) -> PakEntry:
    if pak_type == "A":
        name_raw, offset, size, size_dup, pad, md5, d1, ct, mt, d2 = (
            _TYPE_A_STRUCT.unpack(block)
        )
        return PakEntry(
            _parse_name(name_raw), offset, size, size_dup, pad, md5, d1, ct, mt, d2
        )
    if pak_type == "B":
        pad, md5, d1, size, name_raw, size_dup, offset, mt, ct, d2 = (
            _TYPE_B_STRUCT.unpack(block)
        )
        return PakEntry(
            _parse_name(name_raw), offset, size, size_dup, pad, md5, d1, ct, mt, d2
        )
    # TypeF
    d2, name_raw, offset, size, size_dup, pad, md5, d1, ct, mt = _TYPE_F_STRUCT.unpack(
        block
    )
    return PakEntry(
        _parse_name(name_raw), offset, size, size_dup, pad, md5, d1, ct, mt, d2
    )


class GamePak:
    """Read-only view of an ArcheAge game_pak (AAPack)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.pak_type: str = ""
        self.file_count = 0
        self.extra_file_count = 0
        self._fat_offset = 0
        self._entries: dict[str, PakEntry] = {}
        self._extra: list[PakEntry] = []
        self._read_header()

    # ---- header / FAT -------------------------------------------------
    def _read_header(self) -> None:
        with open(self.path, "rb") as f:
            f.seek(-HEADER_SIZE, 2)
            raw = f.read(HEADER_SIZE)

        data = _decrypt(raw)
        if data[:4] == b"WIBO":
            self.pak_type = "A"
            self.file_count = struct.unpack_from("<I", data, 8)[0]
            self.extra_file_count = struct.unpack_from("<I", data, 12)[0]
        elif data[8:12] == b"IDEJ":
            self.pak_type = "B"
            self.file_count = struct.unpack_from("<I", data, 12)[0]
            self.extra_file_count = struct.unpack_from("<I", data, 0)[0]
        elif data[:4] == b"ZERO":
            self.pak_type = "F"
            self.file_count = struct.unpack_from("<I", data, 8)[0]
            self.extra_file_count = struct.unpack_from("<I", data, 12)[0]
        else:
            raise ValueError(
                f"{self.path}: not a valid game_pak (no WIBO/IDEJ/ZERO marker)"
            )

        total = self.file_count + self.extra_file_count
        total_info_size = total * FILE_INFO_SIZE
        end = self.path.stat().st_size
        fat_offset = end - HEADER_SIZE - total_info_size
        fat_offset -= fat_offset % 0x200  # align down to 512
        self._fat_offset = fat_offset

        with open(self.path, "rb") as f:
            f.seek(fat_offset)
            fat = f.read(total * FILE_INFO_SIZE)
        self._parse_fat(fat)

    def _parse_fat(self, fat: bytes) -> None:
        to_go_files = self.file_count
        to_go_extra = self.extra_file_count
        for i in range(self.file_count + self.extra_file_count):
            block = _decrypt(fat[i * FILE_INFO_SIZE : (i + 1) * FILE_INFO_SIZE])
            entry = _parse_entry(block, self.pak_type)
            if self.pak_type in ("A", "F"):
                if to_go_files > 0:
                    to_go_files -= 1
                    self._entries[entry.name] = entry
                elif to_go_extra > 0:
                    to_go_extra -= 1
                    self._extra.append(entry)
            else:  # TypeB: extras first, files last
                if to_go_extra > 0:
                    to_go_extra -= 1
                    self._extra.append(entry)
                elif to_go_files > 0:
                    to_go_files -= 1
                    self._entries[entry.name] = entry

    # ---- public API ----------------------------------------------------
    def list_entries(self, filter_: str | None = None) -> list[tuple[str, int]]:
        """All (name, size) pairs, optionally filtered by case-insensitive substring."""
        if filter_ is None:
            return [(e.name, e.size) for e in self._entries.values()]
        low = filter_.lower()
        return [
            (e.name, e.size) for e in self._entries.values() if low in e.name.lower()
        ]

    def file_size(self, name: str) -> int | None:
        e = self._entries.get(name)
        return e.size if e else None

    def extract(self, name: str, out_path: str | Path) -> bool:
        """Extract one entry to out_path (raw bytes). Returns False if missing."""
        e = self._entries.get(name)
        if e is None:
            return False
        with open(self.path, "rb") as f:
            f.seek(e.offset)
            data = f.read(e.size)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(data)
        return True

    def extract_prefix(self, prefix: str, out_dir: str | Path) -> int:
        """Extract all entries whose name starts with prefix. Returns count."""
        out_dir = Path(out_dir)
        count = 0
        for name, e in self._entries.items():
            if name.lower().startswith(prefix.lower()):
                target = out_dir / name.replace("\\", "/")
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "rb") as f:
                    f.seek(e.offset)
                    target.write_bytes(f.read(e.size))
                count += 1
        return count

    def stream(self, name: str) -> Iterator[bytes]:
        """Yield raw file bytes in chunks (avoids loading big files at once)."""
        e = self._entries.get(name)
        if e is None:
            return
        with open(self.path, "rb") as f:
            f.seek(e.offset)
            remaining = e.size
            while remaining > 0:
                chunk = f.read(min(1 << 20, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def close(self) -> None:  # no-op, kept for API symmetry
        pass


def open_pak(path: str | Path) -> GamePak:
    return GamePak(path)


__all__ = ["open_pak", "GamePak", "PakEntry", "XLGAMES_KEY"]
