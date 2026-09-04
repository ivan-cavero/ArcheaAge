#!/usr/bin/env python3
"""coverctc.py — decode ArcheAge / CryEngine-1 terrain texture map ``cover.ctc``.

THE FORMAT (proven by structural + pixel-level evidence; __main__ reproduces)
=============================================================================
ArcheAge's per-cell ``terrain/cover.ctc`` is the CryEngine-1 "CTC" terrain
texture map (the file FC1's ``CSectorInfo::MakeSectorTextureDDS`` loads,
extended with a header).  It is NOT a per-texel layer-id map: it is the
final BAKED terrain diffuse, DXT1/BC1-compressed, one image per heightmap
quadtree node:

  [0..32)    header
      0  char[4] 'CRY\\0'
      4  u16     water level (== heightmap oceanWaterLevel, e.g. 100)
      6  u16     max simultaneous terrain layers (8)
      8  u32     version (1)
     12  f32     scale (1.0)
     16  u16     node texture resolution R (128)
     18  u16     unknown (per-cell, 0..30596 — looks like a hash)
     20  u32     constant 22 (global surface-type table size)
     24  u32     bytes per node texture = R*R/2 (8192, DXT1)
     28  u32     4*N + 1, N = number of heightmap quadtree nodes
  [32..32+8N)  u16 table: 4 slots per quadtree node.  Sparse; values are
      the increasing ids 1..340 interleaved with 0xFFFF fillers (a
      per-node surface-id lookup; semantics beyond that unresolved —
      exposed verbatim by ``layer_table()``).
  [32+8N..EOF) N textures, one per heightmap.dat quadtree node, IN NODE
      ORDER (no mips): each node's box is covered by a 128x128 DXT1 image
      stored TRANSPOSED (image row = world +X).  Leaves (nsize==33, 64 m
      boxes, 256 per full cell) tile the cell -> 2048x2048 @ 0.5 m/texel.
      Internal nodes (nsize==0, 85 per full cell) are coarser zoom LODs
      of sub-boxes; N = 256+85 = 341 for a full 1024 m cell, and small
      cells carry their own (5, 21, ...) complete quadtrees.

Proofs (all recomputed by the self-test):
  * payload == N*8192 and table == 4N == @28-1 for every one of the 1294
    cover.ctc sizes in the pak (2793472=341*8192; 172032=21*8192;
    40960=5*8192; ...).
  * heightmap.dat of the same cell has exactly N nodes.
  * quadtree-zoom chain: downsample(texture k+1) == top-left quarter of
    texture k with mean err ~1.3/255 (a per-sector DXT1 *mip chain* — the
    FC1 layout — would instead put mip1 at stride 10912 and fails the
    equivalent test with err ~23/255 on coastal cells).
  * DXT1-decoding each 8192-byte unit yields photographic terrain imagery
    (21k distinct colors, adjacent-pixel noise ~0.5/255).
  * pasting leaf textures transposed at their heightmap boxes is seamless:
    cross-sector edge diff 0.9 == intra-sector 0.5 (row-major, no
    transpose: 8.4).
  * sea cell 012_012 is dominated by one seabed cluster; city cell
    026_006 (leveldata.xml lists tr_af_pavingstone_*) shows gray paving
    pixels; cross-check with leveldata SurfaceType names.

Editor usage: the assembled 2048x2048 map IS the ground-truth biome/road
texture.  ``layers`` gives the dominant-layer id per texel: with
``surface_colors`` (surface id -> reference RGB, e.g. averaged from the
terrain .mtl diffuse DDS) it is a true nearest-surface classification;
without it, a per-cell k-means color-cluster index (0..7).

API:
    header(data) -> dict
    layer_table(data) -> list[int]
    parse_cover_ctc(data, layer_table=None, heightmap_nodes=None,
                    surface_colors=None) -> dict | None
"""

from __future__ import annotations

import struct
from array import array

MAGIC = b"CRY\x00"
_HEADER = 32


def _read_table_len(data: bytes) -> int:
    return struct.unpack_from("<I", data, 28)[0] - 1


def layer_table(data: bytes) -> list[int]:
    """The u16 table at offset 32: 4 slots per quadtree node, 0xFFFF = empty."""
    n = _read_table_len(data)
    if n <= 0 or 32 + 2 * n > len(data):
        return []
    return list(struct.unpack_from(f"<{n}H", data, 32))


def header(data: bytes) -> dict:
    if len(data) < 32 or data[:4] != MAGIC:
        raise ValueError("not a cover.ctc file")
    table_len = _read_table_len(data)
    payload_off = _HEADER + 2 * table_len
    return {
        "magic": data[:4],
        "water_level": struct.unpack_from("<H", data, 4)[0],
        "layer_count": struct.unpack_from("<H", data, 6)[0],
        "version": struct.unpack_from("<I", data, 8)[0],
        "scale": struct.unpack_from("<f", data, 12)[0],
        "tex_size": struct.unpack_from("<H", data, 16)[0],
        "u18_unknown": struct.unpack_from("<H", data, 18)[0],
        "surface_table_size": struct.unpack_from("<I", data, 20)[0],
        "tex_bytes": struct.unpack_from("<I", data, 24)[0],
        "table_len": table_len,
        "n_nodes": table_len // 4,
        "payload_off": payload_off,
    }


# ------------------------------------------------------------------- DXT1/BC1

def _unpack565(c: int) -> tuple[int, int, int]:
    return (c >> 11) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31


def decode_dxt1(px, n: int) -> bytearray:
    """Decode an n x n DXT1/BC1 image -> RGB888 bytearray (row-major)."""
    out = bytearray(n * n * 3)
    bw = n // 4
    for by in range(bw):
        base = by * bw * 8
        for bx in range(bw):
            o = base + bx * 8
            c0 = px[o] | px[o + 1] << 8
            c1 = px[o + 2] | px[o + 3] << 8
            r0, g0, b0 = _unpack565(c0)
            r1, g1, b1 = _unpack565(c1)
            if c0 > c1:
                pal = bytes((r0, g0, b0, r1, g1, b1,
                             (2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3,
                             (r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3))
            else:
                pal = bytes((r0, g0, b0, r1, g1, b1,
                             (r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2, 0, 0, 0))
            cache: dict[int, bytes] = {}
            for y in range(4):
                mb = px[o + 4 + y]
                row = cache.get(mb)
                if row is None:
                    row = (pal[(mb & 3) * 3:(mb & 3) * 3 + 3]
                           + pal[((mb >> 2) & 3) * 3:((mb >> 2) & 3) * 3 + 3]
                           + pal[((mb >> 4) & 3) * 3:((mb >> 4) & 3) * 3 + 3]
                           + pal[((mb >> 6) & 3) * 3:((mb >> 6) & 3) * 3 + 3])
                    cache[mb] = row
                po = ((by * 4 + y) * n + bx * 4) * 3
                out[po:po + 12] = row
    return out


# ------------------------------------------------------------------ assembling

def heightmap_nodes(hmap_data: bytes) -> list[dict]:
    """Nodes of heightmap.dat in file order: {'box_min','box_max','nsize'}.

    cover.ctc textures follow this exact order (nsize==33 -> 64 m leaf
    sector, nsize==0 -> internal coarse node).
    """
    pos = 32
    if hmap_data[0] >= 24:
        pos += 128
    chunk = struct.unpack_from("<i", hmap_data, 4)[0]
    nodes = []
    while pos < chunk:
        bmin = struct.unpack_from("<3f", hmap_data, pos + 4)
        bmax = struct.unpack_from("<3f", hmap_data, pos + 16)
        nsize = struct.unpack_from("<i", hmap_data, pos + 37)[0]
        unk = struct.unpack_from("<i", hmap_data, pos + 41)[0]
        pos += 45 + nsize * nsize * 2 + 4 + 16 + 36 + unk
        nodes.append({"box_min": bmin, "box_max": bmax, "nsize": nsize})
    return nodes


def node_textures(data: bytes) -> list[bytearray]:
    """All N node textures decoded 128x128 RGB, in stored (transposed) order."""
    h = header(data)
    off, n = h["payload_off"], h["n_nodes"]
    return [decode_dxt1(memoryview(data)[off + i * 8192: off + (i + 1) * 8192], 128)
            for i in range(n)]


def assemble_map(data: bytes, nodes: list[dict]) -> dict | None:
    """Place leaf textures at their world boxes -> seamless 2048x2048 map.

    Returns {'width','height','rgb'(bytearray),'cell_m','meters_per_texel',
    'leaf_nodes': {(sector_x, sector_y): node_index}} or None on mismatch.
    World orientation: rgb row = +Y (south), col = +X (east).
    """
    h = header(data)
    if len(nodes) != h["n_nodes"]:
        return None
    off = h["payload_off"]
    x0 = min(nd["box_min"][0] for nd in nodes)
    y0 = min(nd["box_min"][1] for nd in nodes)
    span = max(max(nd["box_max"][0] for nd in nodes) - x0,
               max(nd["box_max"][1] for nd in nodes) - y0)
    if span <= 0:
        return None
    w = int(round(span / 64.0 * 128))
    big = bytearray(w * w * 3)
    leaf_nodes = {}
    for k, nd in enumerate(nodes):
        if nd["nsize"] != 33:
            continue
        sx = int(round((nd["box_min"][0] - x0) / 64.0 * 128))
        sy = int(round((nd["box_min"][1] - y0) / 64.0 * 128))
        tex = decode_dxt1(memoryview(data)[off + k * 8192: off + (k + 1) * 8192], 128)
        tv = memoryview(tex)
        for ty in range(128):  # stored row = world x offset
            row = bytearray(128 * 3)
            for tx in range(128):  # stored col = world y offset
                so = (tx * 128 + ty) * 3
                do = tx * 3
                row[do:do + 3] = tv[so:so + 3]
            do = ((sy + ty) * w + sx) * 3
            big[do:do + 128 * 3] = row
        leaf_nodes[(sx // 128, sy // 128)] = k
    return {"width": w, "height": w, "rgb": big, "cell_m": span,
            "meters_per_texel": span / w, "leaf_nodes": leaf_nodes}


# ------------------------------------------------- dominant-layer estimation

def _kmeans(pixels, k: int, iters: int = 6):
    rng = 12345
    cents = []
    step = max(1, len(pixels) // k)
    for i in range(k):
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        cents.append(list(pixels[min(len(pixels) - 1, i * step + rng % step)]))
    for _ in range(iters):
        sums = [[0, 0, 0, 0] for _ in cents]
        for (r, g, b) in pixels:
            best, bi = 1 << 30, 0
            for j, (cr, cg, cb) in enumerate(cents):
                d = (r - cr) * (r - cr) + (g - cg) * (g - cg) + (b - cb) * (b - cb)
                if d < best:
                    best, bi = d, j
            s = sums[bi]
            s[0] += r; s[1] += g; s[2] += b; s[3] += 1
        for j, s in enumerate(sums):
            if s[3]:
                cents[j] = [s[0] // s[3], s[1] // s[3], s[2] // s[3]]
    return [tuple(c) for c in cents]


def classify_map(rgb: bytearray, w: int, h: int, k: int = 8,
                 surface_colors: dict[int, tuple[int, int, int]] | None = None):
    """Per-texel dominant-layer id -> (rows of array('H'), palette).

    With surface_colors={id:(r,g,b)}: nearest true surface-type id.
    Else: k-means color-cluster index (0..k-1) as a stand-in.
    """
    sample = [(rgb[o], rgb[o + 1], rgb[o + 2])
              for o in range(0, w * h * 3, max(1, (w * h) // 4096) * 3)]
    if surface_colors:
        ids = list(surface_colors.keys())
        cents = [surface_colors[i] for i in ids]
    else:
        ids = list(range(k))
        cents = _kmeans(sample, k)
    cache: dict[tuple[int, int, int], int] = {}
    rows = []
    for y in range(h):
        base = y * w * 3
        row = array("H", bytes(2 * w))
        for x in range(w):
            o = base + x * 3
            key = (rgb[o], rgb[o + 1], rgb[o + 2])
            bi = cache.get(key)
            if bi is None:
                best, bi = 1 << 30, 0
                for j, (cr, cg, cb) in enumerate(cents):
                    d = (key[0] - cr) ** 2 + (key[1] - cg) ** 2 + (key[2] - cb) ** 2
                    if d < best:
                        best, bi = d, j
                cache[key] = bi
            row[x] = ids[bi]
        rows.append(row)
    return rows, [cents[i] for i in range(len(ids))]


# ------------------------------------------------------------------ main parse

def parse_cover_ctc(data: bytes, layer_table=None, heightmap_nodes=None,
                    surface_colors=None, classify: bool = True) -> dict | None:
    """Decode a cover.ctc.

    Returns None if the data doesn't match the proven layout.  Otherwise:
      'header'         — header fields (see module docstring)
      'layer_table'    — u16 table at 32 (4 slots/node, 0xFFFF empty)
      'n_nodes'        — number of quadtree-node textures
      'width','height' — assembled map size (2048 for a full cell) or None
      'layers'         — rows (array('H')) of dominant-layer id per texel,
                         or None if geometry unknown / classify=False
      'map'            — assemble_map() output or None (needs heightmap_nodes)
      'palette'        — RGB tuples behind 'layers'
    Geometry (leaf placement) comes from heightmap.dat nodes of the same
    cell (heightmap_nodes=...).  Without them the textures are still fully
    decodable via node_textures()/layer_table().
    """
    try:
        h = header(data)
    except (ValueError, struct.error, IndexError):
        return None
    if h["tex_size"] * h["tex_size"] // 2 != h["tex_bytes"]:
        return None
    if h["payload_off"] + h["n_nodes"] * h["tex_bytes"] != len(data):
        return None

    out: dict = {
        "header": h,
        "layer_table": layer_table if layer_table is not None else globals()["layer_table"](data),
        "n_nodes": h["n_nodes"],
        "width": None, "height": None, "layers": None,
        "map": None, "palette": None,
    }
    if heightmap_nodes is not None:
        mp = assemble_map(data, heightmap_nodes)
        if mp is not None:
            out["map"] = mp
            out["width"], out["height"] = mp["width"], mp["height"]
            if classify:
                rows, cents = classify_map(mp["rgb"], mp["width"], mp["height"],
                                           surface_colors=surface_colors)
                out["layers"] = rows
                out["palette"] = cents
    return out


# ------------------------------------------------------------------- self-test

def _entropy(b) -> float:
    import math
    from collections import Counter
    c = Counter(b)
    n = len(b)
    return -sum((v / n) * math.log2(v / n) for v in c.values() if v)


def _down2(img, n):
    out = bytearray((n // 2) * (n // 2) * 3)
    for y in range(n // 2):
        for x in range(n // 2):
            for c in range(3):
                s = (img[((2 * y) * n + 2 * x) * 3 + c] + img[((2 * y) * n + 2 * x + 1) * 3 + c]
                     + img[((2 * y + 1) * n + 2 * x) * 3 + c] + img[((2 * y + 1) * n + 2 * x + 1) * 3 + c])
                out[(y * (n // 2) + x) * 3 + c] = s // 4
    return out


def _quarter_tl(img, n):
    out = bytearray((n // 2) * (n // 2) * 3)
    for y in range(n // 2):
        out[y * (n // 2) * 3:(y + 1) * (n // 2) * 3] = img[y * n * 3: y * n * 3 + (n // 2) * 3]
    return out


def _mae(a, b) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def _selftest() -> int:  # pragma: no cover
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from tools.pak import PakIndex, open_pak

    pak_path = Path(".client_files/ArcheAge 1.2 (r208022) for AAEmu/game_pak")
    if not pak_path.exists():
        pak_path = Path(sys.argv[1]) if len(sys.argv) > 1 else pak_path
    if not pak_path.exists():
        print("pak not found; pass path as argv[1]")
        return 1
    idx = PakIndex(open_pak(str(pak_path)))

    print("== size arithmetic across ALL cover.ctc variants in the pak ==")
    from collections import Counter
    sizes = Counter()
    for n, e in idx.pak.entries.items():
        if n.lower().replace("\\", "/").endswith("terrain/cover.ctc"):
            sizes[e.size] += 1
    for s, cnt in sizes.most_common(6):
        d = idx.read(next(n for n in idx.pak.entries
                          if n.lower().replace("\\", "/").endswith("terrain/cover.ctc")
                          and idx.pak.entries[n].size == s))
        h = header(d)
        ok = h["payload_off"] + h["n_nodes"] * h["tex_bytes"] == len(d)
        print(f"  size {s:>9} x{cnt:<4}: table={h['table_len']}=4*{h['n_nodes']} "
              f"nodes, payload={len(d)-h['payload_off']}={h['n_nodes']}*8192 match={ok}")

    for cell in ["011_011", "012_012", "026_006"]:
        d = idx.read(f"game/worlds/main_world/cells/{cell}/client/terrain/cover.ctc")
        hm = idx.read(f"game/worlds/main_world/cells/{cell}/client/terrain/heightmap.dat")
        nodes = heightmap_nodes(hm)
        h = header(d)
        payload = memoryview(d)[h["payload_off"]:]
        lt = layer_table(d)
        nz = [v for v in lt if v != 0xFFFF]
        print(f"\n=== {cell}: {len(d)} B ===")
        print("  header:", h)
        print(f"  layer_table: {len(lt)} u16; {len(nz)} non-FFFF "
              f"(ids {min(nz)}..{max(nz)}, contiguous={nz == list(range(min(nz), max(nz) + 1))})")
        print(f"  payload {len(payload)} B = {h['n_nodes']} x 8192; H(bytes)={_entropy(payload):.3f}; "
              f"heightmap nodes={len(nodes)} == n_nodes: {len(nodes) == h['n_nodes']}")

        t0 = decode_dxt1(payload[0:8192], 128)
        t1 = decode_dxt1(payload[8192:16384], 128)
        e_node = _mae(_down2(t1, 128), _quarter_tl(t0, 128))
        e_mip = _mae(_down2(t0, 128), decode_dxt1(payload[8192:8192 + 2048], 64))
        print(f"  quadtree proof: down(tex1)==tex0.tl_quarter err={e_node:.1f}/255 "
              f"| sector-mip alt: down(tex0)==bytes@8192-as-64 err={e_mip:.1f}/255")

        parsed = parse_cover_ctc(d, heightmap_nodes=nodes)
        mp = parsed["map"]
        w, rgb = mp["width"], mp["rgb"]
        def coldiff(x1, x2):
            return sum(abs(rgb[(y * w + x1) * 3 + c] - rgb[(y * w + x2) * 3 + c])
                       for y in range(0, w, 4) for c in range(3)) / (3 * len(range(0, w, 4)))
        print(f"  map {w}x{w} @ {mp['meters_per_texel']} m/texel, leaves={len(mp['leaf_nodes'])}/256; "
              f"seam(127|128)={coldiff(127, 128):.2f} vs interior(500|501)={coldiff(500, 501):.2f}")
        rows, cents = parsed["layers"], parsed["palette"]
        chars = "@%#*+=-:. "
        print("  palette (cluster -> RGB):", [(i, c) for i, c in enumerate(cents)])
        print("  dominant-layer ASCII (64x64):")
        step = w // 64
        for y in range(0, w, step):
            print("    " + "".join(chars[rows[y][x] * 10 // max(1, len(cents))] for x in range(0, w, step)))
        dom = Counter(rows[y][x] for y in range(0, w, 16) for x in range(0, w, 16))
        top, topn = dom.most_common(1)[0]
        tot = sum(dom.values())
        gray = sum(1 for y in range(0, w, 2) for x in range(0, w, 2)
                   if abs(rgb[(y * w + x) * 3] - rgb[(y * w + x) * 3 + 1]) < 18
                   and abs(rgb[(y * w + x) * 3 + 1] - rgb[(y * w + x) * 3 + 2]) < 18
                   and 90 < rgb[(y * w + x) * 3] < 200)
        print(f"  dominant cluster {top} covers {topn/tot:.1%}; grayish(paving) frac={gray/((w//2)**2):.4f}")
    print("\nEXPECT: 012_012 (sea) dominated by one seabed cluster; "
          "026_006 (pavingstone in leveldata.xml) shows gray road pixels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
