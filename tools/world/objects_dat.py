"""Parse CryEngine cell object.dat (AAEmu ObjectsFile layout)."""

from __future__ import annotations

import struct
from pathlib import Path

BRUSH = 1
VEG = 2
BRUSH_SIZE = 0x84  # 132
VEG_SIZE = 68


def _cstr(buf: bytes) -> str:
    return buf.split(b"\x00", 1)[0].decode("latin-1", "replace").strip()


def parse_objects_dat(data: bytes) -> dict:
    if len(data) < 8:
        return {"assets": [], "brushes": []}
    n = struct.unpack_from("<I", data, 0)[0]
    off = 4
    assets = []
    for _ in range(n):
        if off + 260 > len(data):
            break
        unk = struct.unpack_from("<I", data, off)[0]
        name = _cstr(data[off + 4 : off + 260])
        assets.append({"unknown": unk, "path": name})
        off += 260

    brushes = []
    if off + 4 > len(data):
        return {"assets": assets, "brushes": brushes}
    prefab_count = struct.unpack_from("<I", data, off)[0]
    off += 4
    # skip prefab path table
    skip = prefab_count * 260
    if off + skip <= len(data):
        off += skip

    def walk(node_off: int) -> int:
        if node_off + 33 > len(data):
            return node_off
        _unk = struct.unpack_from("<i", data, node_off)[0]
        block_size = struct.unpack_from("<i", data, node_off + 0x1C)[0]
        child_bits = data[node_off + 0x20]
        content = node_off + 33
        child = content
        if block_size > 0:
            end = content + block_size
            if end <= len(data):
                parse_block(data[content:end], assets, brushes)
            child = end
        cur = child
        if child_bits:
            for i in range(8):
                if child_bits & (1 << i):
                    cur = walk(cur)
        return cur

    if off < len(data):
        walk(off)
    return {"assets": assets, "brushes": brushes}


def parse_block(block: bytes, assets: list, brushes: list) -> None:
    off = 0
    while off + 4 <= len(block):
        typ = struct.unpack_from("<i", block, off)[0]
        if typ == BRUSH:
            if off + BRUSH_SIZE > len(block):
                break
            path_id = struct.unpack_from("<i", block, off + 0x7F)[0]
            # Matrix3x4 at 0x47: 3 rows of 4 floats, translation in m14/m24/m34
            m = struct.unpack_from("<12f", block, off + 0x47)
            path = ""
            if 0 <= path_id < len(assets):
                path = assets[path_id]["path"]
            if path:
                brushes.append(
                    {
                        "path": path,
                        "pathId": path_id,
                        "matrix": list(m),
                    }
                )
            off += BRUSH_SIZE
        elif typ == VEG:
            if off + VEG_SIZE > len(block):
                break
            off += VEG_SIZE
        else:
            # unknown — stop this block rather than desync
            break


def parse_objects_file(path: Path) -> dict:
    return parse_objects_dat(path.read_bytes())


def matrix_translation(m: list[float]) -> tuple[float, float, float]:
    """CryEngine Matrix34 translation = last column."""
    return m[3], m[7], m[11]


def matrix_to_three(m: list[float]) -> list[float]:
    """3x4 Z-up game matrix → three.js 4x4 column-major Y-up.

    Game columns: [x_axis | y_axis | z_axis | translation]
    stored row-major: r0=c0.x c1.x c2.x t.x, etc.
    After (x,y,z)->(x,z,y): axes (ax,ay,az)->(ax,az,ay).
    """
    # rows of 3x4
    r0 = m[0:4]
    r1 = m[4:8]
    r2 = m[8:12]
    # columns (axes + translation) in game space
    ax, ay, az, t = (
        (r0[0], r1[0], r2[0]),
        (r0[1], r1[1], r2[1]),
        (r0[2], r1[2], r2[2]),
        (r0[3], r1[3], r2[3]),
    )
    # map each vector (x,y,z) → (x,z,y)
    def yup(v):
        return (v[0], v[2], v[1])

    ax, ay, az, t = yup(ax), yup(ay), yup(az), yup(t)
    # three.js Matrix4 column-major: col0=ax, col1=ay_mapped was game Y → now three Z
    # After yup, game Y-axis is three Z-axis (index 2), game Z-axis is three Y-axis.
    # We want three axes X,Y,Z = game X, game Z, game Y
    tx, ty, tz = t
    gx, gy, gz = ax, az, ay  # three X,Y,Z axes
    return [
        gx[0], gx[1], gx[2], 0,
        gy[0], gy[1], gy[2], 0,
        gz[0], gz[1], gz[2], 0,
        tx, ty, tz, 1,
    ]
