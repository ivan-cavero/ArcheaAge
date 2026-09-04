"""Minimal CryEngine CHR (character/skeletal mesh) bind-pose reader.

ArcheAge .chr files share the 'CryTek' chunked container with .cgf, but the
chunk table lies twice over:

* the table is NOT limited to the declared nChunks — the real mesh lives in
  0xCCCC0017 MeshSubsets + 0xCCCC0016 DataStream chunks listed in *extra*
  table entries that follow the 0xACDC000X skeleton/skin chunks (and, for
  .chr files with embedded animations, 0xAAFC0004 CAF chunks);
* _chunk_stride() from cgf rejects 0xAAFC types, so a stride-20 file that
  has CAF chunks inside the first nChunks rows reads as stride 16 garbage —
  we re-detect with the 0xCCCC/0xACDC/0xAAFC mask.

Streams are the same ver-0x800 layout parse_cgf already reads: st 0=vtx(f32x3)
1=nrm 2=uv(f32x2) 5=idx(u16/u32); st 6 (tangent), 9 (bone weights) and the
0xACDC0001 "Skin" chunk are ignored (bind pose, no animation needed).

PC nude hosts (e.g. nu_m_base.chr) carry only a 3-vertex helper stub plus
morph data; their real body geometry lives in the sibling *_nude.chr, which
this parser reads just the same.
"""

from __future__ import annotations

import struct
from pathlib import Path

from tools.world.cgf import _SKIP, _cstr


def _chr_stride(data: bytes) -> int:
    """CHR chunk-table entry size (16 for ver 0x744, 20 for 0x745).

    Same idea as cgf._chunk_stride but (a) 0xAAFC (CAF animation) chunks count
    as valid too — they sit inside the declared nChunks of many .chr files and
    would otherwise poison the test — and (b) we score both strides by how
    many consecutive well-formed rows they yield, because the declared nChunks
    is unreliable (it can exceed or fall short of the real row count).
    """
    best_stride, best_n = 16, -1
    for stride in (20, 16):
        n = 0
        while True:
            o = 24 + n * stride
            if o + 16 > len(data):
                break
            t, _v, off, _cid = struct.unpack_from("<4I", data, o)
            if (t & 0xFFFFFF00) not in (0xCCCC0000, 0xACDC0000, 0xAAFC0000):
                break
            if off + 16 >= len(data):
                break
            n += 1
        if n > best_n:
            best_stride, best_n = stride, n
    return best_stride


def _chr_chunks(data: bytes) -> list[tuple[int, int, int, int]]:
    """All chunk-table entries (see _chr_stride for why nChunks is ignored)."""
    nchunks = struct.unpack_from("<I", data, 16)[0]
    if nchunks == 0 or nchunks > 8192:
        return []
    stride = _chr_stride(data)
    entries: list[tuple[int, int, int, int]] = []
    i = 0
    while i < 8192:
        o = 24 + i * stride
        if o + 16 > len(data):
            break
        t, v, off, cid = struct.unpack_from("<4I", data, o)
        if (t & 0xFFFFFF00) not in (0xCCCC0000, 0xACDC0000, 0xAAFC0000):
            break
        if off + 16 >= len(data):
            break
        entries.append((t, v, off, cid))
        i += 1
    return entries


def parse_chr(data: bytes) -> dict | None:
    """Extract the bind-pose LOD0 mesh of a .chr as the parse_cgf dict."""
    try:
        return _parse_chr(data)
    except Exception:
        return None


def _parse_chr(data: bytes) -> dict | None:
    if len(data) < 40 or data[:6] != b"CryTek":
        return None
    entries = _chr_chunks(data)
    if not entries:
        return None

    mtl_names: list[str] = []
    streams: dict[int, tuple[bytes, int, int]] = {}
    subsets: list[dict] = []
    got_first_subs = False
    mesh_done = False  # LOD0 vtx+idx collected; later groups are LOD1+

    for t, v, off, cid in entries:
        payload = off + 16
        if t == 0xCCCC0014:  # MtlName (parent 0x12-style list, one chunk each)
            if payload + 8 + 128 > len(data):
                continue
            mtl_names.append(_cstr(data[payload + 8 : payload + 8 + 128]))
        elif t == 0xCCCC0017:  # MeshSubsets
            if got_first_subs:
                mesh_done = True  # a second subset chunk = a later LOD
                continue
            got_first_subs = True
            if payload + 16 > len(data):
                continue
            _flags, nsub = struct.unpack_from("<2I", data, payload)
            for s in range(min(nsub, 256)):
                rec = payload + 16 + s * 36
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
        elif t == 0xCCCC0016:  # DataStream (ver 0x800, same as CGF)
            if mesh_done or payload + 24 > len(data):
                continue
            _flags, st, ne, bpe, _r1, _r2 = struct.unpack_from("<6I", data, payload)
            if ne == 0 or bpe == 0 or ne > 4_000_000 or ne * bpe > len(data) - payload - 24:
                continue
            raw = data[payload + 24 : payload + 24 + ne * bpe]
            if st in (0, 1, 2, 5) and st not in streams:
                streams[st] = (raw, ne, bpe)
            if streams.get(0) and streams.get(5):
                mesh_done = True

    gv = streams.get(0)
    gi = streams.get(5)
    if not gv or not gi or gv[2] != 12:
        return None

    nv = min(gv[1], len(gv[0]) // 12)
    if nv == 0:
        return None
    pos: list[float] = []
    verts = struct.unpack(f"<{nv * 3}f", gv[0][: nv * 12])
    for i in range(nv):
        x, y, z = verts[i * 3], verts[i * 3 + 1], verts[i * 3 + 2]
        pos.extend((x, z, y))  # Z-up → Y-up

    nrm: list[float] = []
    gn = streams.get(1)
    if gn and gn[2] == 12 and len(gn[0]) >= nv * 12:
        nvals = struct.unpack(f"<{nv * 3}f", gn[0][: nv * 12])
        for i in range(nv):
            nx, ny, nz = nvals[i * 3], nvals[i * 3 + 1], nvals[i * 3 + 2]
            nrm.extend((nx, nz, ny))
    else:
        nrm.extend([0.0] * nv * 3)

    uv: list[float] = []
    gu = streams.get(2)
    if gu and gu[1] >= nv:
        if gu[2] == 8 and len(gu[0]) >= nv * 8:
            uv.extend(struct.unpack(f"<{nv * 2}f", gu[0][: nv * 8]))
        elif gu[2] == 4 and len(gu[0]) >= nv * 4:
            for i in range(nv):
                u, vv = struct.unpack_from("<ee", gu[0], i * 4)
                uv.extend((float(u), float(vv)))
    if len(uv) != nv * 2:
        uv.extend([0.0] * (nv * 2 - len(uv)))

    if gi[2] == 2:
        cnt = min(gi[1], len(gi[0]) // 2)
        idx_iter = struct.unpack(f"<{cnt}H", gi[0][: cnt * 2])
    elif gi[2] == 4:
        cnt = min(gi[1], len(gi[0]) // 4)
        idx_iter = struct.unpack(f"<{cnt}I", gi[0][: cnt * 4])
    else:
        return None
    indices = [int(i) for i in idx_iter if int(i) < nv]
    if not indices:
        return None

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


def parse_chr_file(path: Path) -> dict | None:
    try:
        return parse_chr(path.read_bytes())
    except Exception:
        return None
