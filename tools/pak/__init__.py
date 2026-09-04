"""tools.pak — read-only Python access to ArcheAge game_pak (AAPack)."""

from .paklib import GamePak, PakEntry, PakIndex, open_pak

__all__ = ["open_pak", "GamePak", "PakEntry", "PakIndex"]
