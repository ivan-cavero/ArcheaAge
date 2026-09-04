"""Parse CryEngine vegetation.xml groups and per-cell vegetation.dat.

vegetation.dat (verified on 1.2 main_world):
  int32 version (=1)
  uint32 offsets[16]   # 4×4 sectors of 256 m, local XY in 0..256
  uint32 sizes[16]
  then packed 64-byte instances (object.dat type-2 without the type int):
    0x00 Vec3 AABB min (cell-sector local)
    0x0C Vec3 AABB max
    0x37 uint16 group id (unaligned) into vegetation.xml <group id>
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

SECTOR = 256.0
VEG_REC = 64
GROUP_ID_OFF = 55


def parse_vegetation_xml(text: str) -> dict[int, dict]:
    groups: dict[int, dict] = {}
    for m in re.finditer(r"<group\b([^>]*)/?>", text, re.I):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if "id" not in attrs:
            continue
        gid = int(attrs["id"])
        model = (attrs.get("modelFileName") or "").replace("\\", "/")
        if model and not model.lower().startswith("game/"):
            model = "game/" + model.lstrip("/")
        groups[gid] = {
            "id": gid,
            "name": attrs.get("name") or "",
            "model": model,
            "size": float(attrs.get("fSize") or 1.0),
            "sizeVar": float(attrs.get("fSizeVar") or 0.0),
            "randomRot": attrs.get("bRandomRotation") == "1",
        }
    return groups


def parse_vegetation_xml_file(path: Path) -> dict[int, dict]:
    return parse_vegetation_xml(path.read_text(encoding="utf-8", errors="replace"))


def parse_vegetation_dat(data: bytes, groups: dict[int, dict] | None = None) -> list[dict]:
    if len(data) < 132:
        return []
    ver = struct.unpack_from("<I", data, 0)[0]
    if ver not in (0, 1):
        return []
    offs = struct.unpack_from("<16I", data, 4)
    sizes = struct.unpack_from("<16I", data, 68)
    out: list[dict] = []
    groups = groups or {}
    for ci, (off, size) in enumerate(zip(offs, sizes)):
        if size < VEG_REC or off + size > len(data):
            continue
        sx = ci % 4
        sy = ci // 4
        chunk = data[off : off + size]
        n = len(chunk) // VEG_REC
        for i in range(n):
            rec = chunk[i * VEG_REC : (i + 1) * VEG_REC]
            mn = struct.unpack_from("<3f", rec, 0)
            mx = struct.unpack_from("<3f", rec, 12)
            gid = struct.unpack_from("<H", rec, GROUP_ID_OFF)[0]
            info = groups.get(gid) or {}
            model = info.get("model") or ""
            if not model:
                continue
            cx = sx * SECTOR + (mn[0] + mx[0]) * 0.5
            cy = sy * SECTOR + (mn[1] + mx[1]) * 0.5
            cz = (mn[2] + mx[2]) * 0.5
            dx = abs(mx[0] - mn[0])
            dy = abs(mx[1] - mn[1])
            dz = abs(mx[2] - mn[2])
            seed = (int(cx * 17) ^ int(cy * 31) ^ gid) & 0xFFFF
            yaw = (seed / 65535.0) * 6.28318530718 if info.get("randomRot", True) else 0.0
            size = float(info.get("size") or 1.0)
            svar = float(info.get("sizeVar") or 0.0)
            scale = size * (1.0 + ((seed % 1000) / 1000.0 - 0.5) * 2.0 * svar)
            if scale < 0.15:
                scale = 0.15
            out.append(
                {
                    "group": gid,
                    "name": info.get("name") or "",
                    "model": model,
                    "pos": [round(cx, 3), round(cy, 3), round(cz, 3)],
                    "scale": round(scale, 3),
                    "yaw": round(yaw, 4),
                    "span": round(max(dx, dy, dz), 2),
                }
            )
    return out
