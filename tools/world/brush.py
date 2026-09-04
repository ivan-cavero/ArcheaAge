#!/usr/bin/env python3
"""brush.py — parse ArcheAge per-cell terrain brush.dat (CryEngine brush placements).

brush.dat contains NO inline mesh geometry. Each brush is a 128-byte record
that references a CGF model (PathId -> the cell's statobjs.dat table) plus a
MaterialId (-> the cell's materials.dat table) and a Matrix3x4 transform;
the geometry itself lives in the referenced .cgf (see cgf.py). The record is
byte-for-byte the client object.dat "brush" (type 1) data block minus its
4-byte type dword — same field positions as AAEmu's ObjectDataType1Brush
(Models/CryEngine/Objects/ObjectDataType1Brush.cs: Matrix3x4 @ +0x47,
MaterialId @ +0x77, PathId @ +0x7F, total 0x84, all relative to the type dword).

Layout (little-endian, coordinates cell-local 0..1024 m, Z-up):

  u32 version (= 1)
  u32 sector_offset[256]   byte offset of each 16x16 sector's brush array;
                           empty sectors repeat the following offset
  u32 sector_size[256]     byte size of each sector's brush array (n * 128);
                           sum(sector_size) + 2052 == file size
  then, per sector, n records of 128 bytes:

  +0    float3  aabb_min          terrain-influence bounds (cell-local)
  +12   float3  aabb_max
  +24   float32 0.0 (unused; seen -0.0)
  +28   float32 size metric       grows with brush size, ~surface area (unknown)
  +32   uint8   kind              seen: 0, 1, 8, 9 (8 dominant; rare 40)
  +33   uint8   flags             0x00 | 0x08 | 0x20
  +34   uint8[2] 0x00, 0x20       (constant)
  +36   uint8   param_a           0..255, usually 100
  +37   uint8   param_b           0..255, usually 100
  +38   uint16  0
  +40   uint32  model stamp       0 | small ids (322..684) | 0x02b4a170 | 0x302d0ce8
  +44   uint32  0 | 2
  +48   char[19] name/comment     printable on some brushes ("6> Exporting indoor"),
                                  otherwise a binary u64+u64+u24 union (unknown)
  +67   float32[12] Matrix3x4     row-major M11 M12 M13 tx / M21..ty / M31..tz;
                                  translation sits near the AABB center but is
                                  the model pivot, not always exactly it
  +115  uint32  MaterialId        index into materials.dat
  +119  uint32  flag              0 | 0x30002f00 | 0x415dc000; tracks the +64 tag
  +123  uint32  PathId            index into statobjs.dat (.cgf model path)
  +127  uint8   0                 record is 128 bytes total

  materials.dat / statobjs.dat layout: u32 count + count * 256-byte NUL-padded
  latin-1 path strings (materials.dat has no extension, statobjs.dat is .cgf).

Verified: every PathId < statobjs.dat count and every MaterialId <
materials.dat count in cells 011_011 / 010_012 / 010_011, and the resolved
names correlate (e.g. mat "wood_fence" with path "wood_fence_b.cgf").
"""

from __future__ import annotations

import struct
from pathlib import Path

RECORD_SIZE = 128
SECTORS = 256  # 16x16 terrain sectors
_HEADER = 4 + SECTORS * 8  # version + offset table + size table = 2052

_PATH_ENTRY = 256  # materials.dat / statobjs.dat entry width


def _cstr(buf: bytes) -> str:
    return buf.split(b"\x00", 1)[0].decode("latin-1", "replace")


def read_name_table(data: bytes) -> list[str]:
    """Parse a materials.dat / statobjs.dat string table (u32 count + N*256B)."""
    if len(data) < 4:
        return []
    count = struct.unpack_from("<I", data, 0)[0]
    max_n = (len(data) - 4) // _PATH_ENTRY
    out = []
    for i in range(min(count, max_n)):
        o = 4 + i * _PATH_ENTRY
        out.append(_cstr(data[o : o + _PATH_ENTRY]))
    return out


def _parse_record(data: bytes, off: int, sector: int) -> dict | None:
    if off + RECORD_SIZE > len(data):
        return None
    rec = data[off : off + RECORD_SIZE]
    mn = struct.unpack_from("<3f", rec, 0)
    mx = struct.unpack_from("<3f", rec, 12)
    if any(v != v for v in mn + mx):  # NaN
        return None
    matrix = list(struct.unpack_from("<12f", rec, 67))
    # AAEmu ObjectDataType1Brush layout: MaterialId +0x73, PathId +0x7B (brush frame)
    material_id = struct.unpack_from("<I", rec, 115)[0]
    path_id = struct.unpack_from("<I", rec, 123)[0]
    if material_id > 0xFFFF or path_id > 0xFFFF:
        return None
    pos = [matrix[3], matrix[7], matrix[11]]
    comment_bytes = rec[48:67]
    printable = all(32 <= b < 127 or b == 0 for b in comment_bytes)
    comment = _cstr(comment_bytes).strip() if printable else ""
    return {
        "sector": sector,
        "offset": off,
        "aabb_min": [mn[0], mn[1], mn[2]],
        "aabb_max": [mx[0], mx[1], mx[2]],
        "center": [(mn[i] + mx[i]) / 2 for i in range(3)],
        "pos": pos,  # Matrix3x4 translation (model pivot, cell-local)
        "matrix": matrix,  # row-major 3x4: M11 M12 M13 tx / M21 ... / M31 ...
        "material_id": material_id,  # index into materials.dat
        "path_id": path_id,  # index into statobjs.dat (.cgf model)
        "material": "",  # filled by attach_names()
        "model": "",  # filled by attach_names()
        "kind": rec[32],
        "flags": rec[33],
        "param": [rec[36], rec[37]],
        "model_stamp": struct.unpack_from("<I", rec, 40)[0],
        "size_metric": struct.unpack_from("<f", rec, 28)[0],  # meaning unknown
        "comment": comment,
        "vertices": None,  # brush.dat stores no inline geometry
        "indices": None,
    }


def parse_brush_dat(data: bytes) -> list[dict]:
    """Decode a cell's brush.dat into brush placement records (no geometry)."""
    if len(data) < _HEADER:
        return []
    version = struct.unpack_from("<I", data, 0)[0]
    if version != 1:
        return []
    offsets = struct.unpack_from(f"<{SECTORS}I", data, 4)
    sizes = struct.unpack_from(f"<{SECTORS}I", data, 4 + SECTORS * 4)

    brushes: list[dict] = []
    for sector, (off, size) in enumerate(zip(offsets, sizes)):
        if size % RECORD_SIZE != 0:
            # table mismatch; keep scanning defensively with whole records only
            size -= size % RECORD_SIZE
        end = off + size
        if end > len(data):
            end = len(data) - (len(data) - off) % RECORD_SIZE
        for rec_off in range(off, end, RECORD_SIZE):
            rec = _parse_record(data, rec_off, sector)
            if rec is not None:
                brushes.append(rec)
    return brushes


def attach_names(
    brushes: list[dict],
    materials_data: bytes | None = None,
    statobjs_data: bytes | None = None,
) -> list[dict]:
    """Resolve material_id/path_id to material/model strings in place."""
    materials = read_name_table(materials_data) if materials_data else []
    models = read_name_table(statobjs_data) if statobjs_data else []
    for b in brushes:
        if b["material_id"] < len(materials):
            b["material"] = materials[b["material_id"]]
        if b["path_id"] < len(models):
            b["model"] = models[b["path_id"]]
    return brushes


def parse_brush_dat_file(path: Path) -> list[dict]:
    return parse_brush_dat(path.read_bytes())


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    data = Path(sys.argv[1]).read_bytes()
    recs = parse_brush_dat(data)
    used_sectors = len({r["sector"] for r in recs})
    print(
        f"version={struct.unpack_from('<I', data, 0)[0]} "
        f"records={len(recs)} sectors_with_brushes={used_sectors}/{SECTORS}"
    )
    for r in recs[:10]:
        mn, mx = r["aabb_min"], r["aabb_max"]
        print(
            f"  @{r['offset']:6d} sec={r['sector']:3d} "
            f"aabb=({mn[0]:7.1f},{mn[1]:7.1f},{mn[2]:7.1f})-"
            f"({mx[0]:7.1f},{mx[1]:7.1f},{mx[2]:7.1f}) "
            f"pos=({r['pos'][0]:6.1f},{r['pos'][1]:6.1f},{r['pos'][2]:6.1f}) "
            f"mat={r['material_id']:4d} path={r['path_id']:4d} kind={r['kind']}"
            + (f' comment="{r["comment"]}"' if r["comment"] else "")
        )
