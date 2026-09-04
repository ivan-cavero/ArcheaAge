"""Minimal CryEngine 3 CGF/CGA/CHR mesh reader (chunk table 0x744 / 0x800 streams).

ArcheAge ships a second CGF header layout: magic "CryTek", u32 zero @6,
u16 0xFFFF @10, version (0x0744 / 0x0745) @12, header size (20) @16 and
numChunks at 20 (NOT 16).  0x745 chunk-table entries carry a trailing
u32 chunk-size field (stride 20) while 0x744 stays at stride 16.  The
legacy path (numChunks @16, stride probed by signature scan) is kept as
a fallback so classic files parse unchanged.
"""

from __future__ import annotations

import struct
from pathlib import Path

_SKIP = {"proxy", "nodraw", "nocollide", "nocollde", "helper", "phys", "collision"}

_STREAM = {
    0: "vtx",
    1: "nrm",
    2: "uv",
    3: "col",
    5: "idx",
}


def _cstr(buf: bytes) -> str:
    return buf.split(b"\x00", 1)[0].decode("latin-1", "replace")


# Chunk-type high words seen in real files: 0xCCCC CGF, 0xACDC/0xAAFC CHR &
# aux/collision chunks.
_TABLE_SIGS = (0xCCCC0000, 0xACDC0000, 0xAAFC0000)


def _table_valid(data: bytes, nchunks: int, table: int, stride: int) -> bool:
    """All table entries must carry a known chunk signature and a sane offset."""
    if nchunks == 0 or nchunks > 4096 or table + nchunks * stride > len(data):
        return False
    for i in range(nchunks):
        o = table + i * stride
        if o + 16 > len(data):
            return False
        t, _v, off, _cid = struct.unpack_from("<4I", data, o)
        if (t & 0xFFFFFF00) not in _TABLE_SIGS or off + 16 > len(data):
            return False
    return True


def _chunk_table(data: bytes) -> tuple[int, int, int] | None:
    """Locate the chunk table: (nchunks, table_offset, stride) or None.

    AA layout: u32 0 @6, u16 0xFFFF @10, version 0x0744/0x0745 @12, header
    size @16, numChunks @20.  0x745 entries carry a trailing u32 size so
    their stride is 20; 0x744 stays at 16.  Classic layout (numChunks @16,
    version @6) is handled by the legacy probe below, byte-identical to the
    old behaviour.
    """
    if struct.unpack_from("<I", data, 6)[0] == 0:
        v10, ver = struct.unpack_from("<2H", data, 10)
        if v10 == 0xFFFF:
            nc = struct.unpack_from("<I", data, 20)[0]
            want = 20 if ver == 0x745 else 16
            for stride in (want, 36 - want):
                if _table_valid(data, nc, 24, stride):
                    return nc, 24, stride
    nchunks = struct.unpack_from("<I", data, 16)[0]
    if nchunks == 0 or nchunks > 4096:
        return None
    stride = _chunk_stride(data, nchunks)
    if 24 + nchunks * stride > len(data):
        return None
    return nchunks, 24, stride


def _chunk_stride(data: bytes, nchunks: int) -> int:
    """CryEngine CGF chunk-table entry size.

    Version 0x744 packs entries as 16 bytes (type, version, offset, reserved);
    version 0x745 inserts an extra field making them 20 bytes. Reading one with
    the other stride yields garbage types and the mesh silently fails to load
    (this is why houses/walls/trees vanished). We confirm by requiring every
    declared chunk type to carry the 0xcccc00XX signature.
    """
    table = 24
    for stride in (20, 16):
        ok = True
        for i in range(nchunks):
            o = table + i * stride
            if o + 16 > len(data):
                ok = False
                break
            t = struct.unpack_from("<I", data, o)[0]
            # 0xcccc = CGF chunks, 0xacdc = CHR skeleton/physics chunks
            if (t & 0xFFFFFF00) not in (0xCCCC0000, 0xACDC0000):
                ok = False
                break
        if ok:
            return stride
    return 16


def parse_cgf(data: bytes) -> dict | None:
    if len(data) < 40 or data[:6] != b"CryTek":
        return None
    loc = _chunk_table(data)
    if loc is None:
        return None
    nchunks, table, stride = loc
    chunks = []
    for i in range(nchunks):
        t, v, off, cid = struct.unpack_from("<4I", data, table + i * stride)
        chunks.append((t, v, off, cid))

    mtl_names: list[str] = []
    # DataStream chunks arrive grouped per submesh (vtx, nrm, uv, idx, ...).
    # A file may store SEVERAL LODs — each LOD is one MeshSubsets chunk plus a
    # merged vertex/index set. We keep only LOD0: mixing LOD1 subsets with
    # LOD0's index buffer drew faces at garbage positions ("torn" trees).
    groups: list[dict[int, tuple[bytes, int, int]]] = []
    cur: dict[int, tuple[bytes, int, int]] | None = None
    subsets: list[dict] = []
    got_first_subs = False
    mesh_done = False

    for t, v, off, cid in chunks:
        if off + 16 > len(data):
            continue
        payload = off + 16
        if t == 0xCCCC0014:  # MtlName
            if payload + 8 + 128 + 8 > len(data):
                continue
            name = _cstr(data[payload + 8 : payload + 8 + 128])
            mtl_names.append(name)
        elif t == 0xCCCC0016:  # DataStream 0x800
            if payload + 24 > len(data):
                continue
            if mesh_done:
                continue  # LOD1+ streams — would clobber LOD0's buffers
            _flags, st, ne, bpe, _r1, _r2 = struct.unpack_from("<6I", data, payload)
            if ne == 0 or bpe == 0 or ne > 2_000_000 or ne * bpe > len(data) - payload - 24:
                continue
            raw = data[payload + 24 : payload + 24 + ne * bpe]
            if st == 0:
                if mesh_done:
                    continue  # LOD1+ vertex stream — skip the whole LOD
                cur = {}
                groups.append(cur)
            if cur is None:
                cur = {}
                groups.append(cur)
            cur[st] = (raw, ne, bpe)
            if st == 5 and cur.get(0):
                mesh_done = True  # LOD0 complete (vtx + idx seen)
        elif t == 0xCCCC0017:  # MeshSubsets
            if got_first_subs:
                continue  # subsets of a later LOD
            got_first_subs = True
            if payload + 16 > len(data):
                continue
            _flags, nsub = struct.unpack_from("<2I", data, payload)
            base = payload + 16
            for s in range(min(nsub, 256)):
                rec = base + s * 36
                if rec + 36 > len(data):
                    break
                fi, ni, fv, nv, mid, _rad, _cx, _cy, _cz = struct.unpack_from(
                    "<5I f 3f", data, rec
                )
                subsets.append(
                    {
                        "firstIndex": fi,
                        "indexCount": ni,
                        "firstVertex": fv,
                        "vertexCount": nv,
                        "matId": mid,
                    }
                )

    pos: list[float] = []
    nrm: list[float] = []
    uv: list[float] = []
    indices: list[int] = []
    vbase = 0
    for g in groups:
        gv = g.get(0)
        if not gv or gv[2] != 12:
            continue
        nv = gv[1]
        verts = struct.unpack(f"<{nv * 3}f", gv[0][: nv * 12])
        for i in range(nv):
            x, y, z = verts[i * 3], verts[i * 3 + 1], verts[i * 3 + 2]
            pos.extend((x, z, y))  # Z-up → Y-up
        gn = g.get(1)
        if gn and gn[2] == 12 and gn[1] == nv:
            nvals = struct.unpack(f"<{nv * 3}f", gn[0][: nv * 12])
            for i in range(nv):
                nx, ny, nz = nvals[i * 3], nvals[i * 3 + 1], nvals[i * 3 + 2]
                nrm.extend((nx, nz, ny))
        else:
            nrm.extend([0.0] * nv * 3)
        gu = g.get(2)
        if gu and gu[1] == nv:
            if gu[2] == 8:
                uv.extend(struct.unpack(f"<{nv * 2}f", gu[0][: nv * 8]))
            elif gu[2] == 4:
                for i in range(nv):
                    u, vv = struct.unpack_from("<ee", gu[0], i * 4)
                    uv.extend((float(u), float(vv)))
            else:
                uv.extend([0.0] * nv * 2)
        else:
            uv.extend([0.0] * nv * 2)
        gi = g.get(5)
        if gi:
            if gi[2] == 2:
                idx = struct.unpack(f"<{gi[1]}H", gi[0][: gi[1] * 2])
            elif gi[2] == 4:
                idx = struct.unpack(f"<{gi[1]}I", gi[0][: gi[1] * 4])
            else:
                idx = ()
            indices.extend(i + vbase for i in idx if i + vbase < len(pos) // 3)
        vbase = len(pos) // 3

    if not indices or not pos:
        return None
    nv = len(pos) // 3

    if not subsets:
        subsets = [
            {
                "firstIndex": 0,
                "indexCount": len(indices),
                "firstVertex": 0,
                "vertexCount": nv,
                "matId": 0,
            }
        ]

    children = mtl_names[1:] if len(mtl_names) > 1 else mtl_names
    out_sub = []
    for s in subsets:
        mid = s["matId"]
        name = ""
        if children and mid < len(children):
            name = children[mid]
        elif mtl_names and mid < len(mtl_names):
            name = mtl_names[mid]
        low = name.lower()
        if any(k in low for k in _SKIP):
            continue
        if s["indexCount"] <= 0:
            continue
        fi = min(int(s["firstIndex"]), len(indices))
        ni = min(int(s["indexCount"]), len(indices) - fi)
        if ni <= 0:
            continue
        out_sub.append(
            {
                "firstIndex": fi,
                "indexCount": ni,
                "mat": name,
                "matId": mid,
            }
        )
    if not out_sub:
        return None
    return {
        "positions": pos,
        "normals": nrm,
        "uvs": uv,
        "indices": indices,
        "subsets": out_sub,
        "materials": mtl_names,
    }


def parse_cgf_file(path: Path) -> dict | None:
    return parse_cgf(path.read_bytes())
