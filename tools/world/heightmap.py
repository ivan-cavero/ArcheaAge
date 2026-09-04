#!/usr/bin/env python3
"""heightmap.py — parse ArcheAge cell terrain heightmap.dat.

Faithful port of AAEmu's Hmap/NodeCell readers
(servers/aaemu/AAEmu.Game/Models/ClientData/Hmap.cs, NodeCell.cs).

Format (CryEngine-style quadtree):
  header: 4 bytes (version/dummy/flags/flags2)
          + 5 int32 (chunkSize, hmapSizeInUnits, unitSizeInMeters,
                      sectorSizeInMeters, sectorsTableSize)
          + 2 float32 (heightmapZRatio, oceanWaterLevel)
          + 128 bytes unk (version >= 24)
  then nodes until chunkSize:
    node: 4 bytes (version/dummy/flags/flags2)
          + 6 float32 (AABB min/max)
          + 1 byte (bHasHoles)
          + 2 float32 (fOffset, fRange)
          + 1 int32 (nSize)
          + 1 int32 (unkCount)
          + nSize*nSize uint16 (pHMData)
          + 1 int32 + 4 float32 + 36 + unkCount bytes (trailing)
    if nSize < 33: bilinear upscale to 33x33
    if version < 7: rescale heights to int grid

Cell grid: 16x16 sectors, each 32x32 units -> 512x512 heights per cell.
"""

import struct
from pathlib import Path

# AAEmu WorldManager constants
CELL_SIZE = 1024  # meters
REGION_SIZE = 64  # meters (sector)
SECTORS_PER_CELL = CELL_SIZE // REGION_SIZE  # 16
SECTOR_HMAP_RESOLUTION = REGION_SIZE // 2  # 32
CELL_HMAP_RESOLUTION = CELL_SIZE // 2  # 512

INV5CM = 20
MASK12BIT = (1 << 12) - 1


def _safe_int(v: float, fallback: int = 0) -> int:
    """int() on a float can raise on nan/inf from a corrupt heightmap."""
    try:
        return int(v)
    except (ValueError, OverflowError):
        return fallback


class NodeCell:
    def __init__(self):
        self.version = 0
        self.box_min = (0.0, 0.0, 0.0)
        self.box_max = (0.0, 0.0, 0.0)
        self.b_has_holes = 0
        self.f_offset = 0.0
        self.f_range = 0.0
        self.n_size = 0
        self.p_hm_data = []
        self._i_offset = 0
        self._i_range = 0
        self._i_step = 1

    def read(self, data: bytes, pos: int) -> int:
        """Parse one node from data at pos; returns new position."""
        self.version = data[pos]
        (self.box_min, self.box_max) = (
            struct.unpack_from("<3f", data, pos + 4),
            struct.unpack_from("<3f", data, pos + 16),
        )
        self.b_has_holes = data[pos + 28]
        self.f_offset = struct.unpack_from("<f", data, pos + 29)[0]
        self.f_range = struct.unpack_from("<f", data, pos + 33)[0]
        self.n_size = struct.unpack_from("<i", data, pos + 37)[0]
        unk_count = struct.unpack_from("<i", data, pos + 41)[0]

        hm_start = pos + 45
        self.p_hm_data = list(
            struct.unpack_from(f"<{self.n_size * self.n_size}H", data, hm_start)
        )
        pos = hm_start + self.n_size * self.n_size * 2
        pos += 4 + 16 + 36 + unk_count  # trailing int32 + 4 floats + blob

        self._init()
        if self.version < 7:
            self._rescale_to_int()
        self._upscale()
        return pos

    def _init(self):
        f_min = self.f_offset
        f_max = f_min + 0xFFF0 * self.f_range
        self._i_offset = _safe_int(f_min * INV5CM)
        self._i_range = _safe_int((f_max - f_min) * INV5CM)
        self._i_step = (
            (self._i_range + MASK12BIT - 1) // MASK12BIT if self._i_range > 0 else 1
        )

    def _rescale_to_int(self):
        for i, hraw in enumerate(self.p_hm_data):
            height = self.f_min() + (0xFFF0 & hraw) * self.f_range
            hdec = _safe_int((height - self.f_min()) * INV5CM) // self._i_step
            self.p_hm_data[i] = (hraw & 0xF) | (hdec << 4)

    def f_min(self):
        return self.f_offset

    def f_max(self):
        return self.f_offset + 0xFFF0 * self.f_range

    def _upscale(self):
        n = self.n_size
        if n > 0 and n < 33:
            source_scale = n / 33.0
            result = [0] * (33 * 33)
            for target_x in range(33):
                for target_y in range(33):
                    index = target_x * 33 + target_y
                    source_x = _safe_int(target_x * source_scale)
                    source_y = _safe_int(target_y * source_scale)
                    # nearest significant points (AAEmu keeps it 1x1 here)
                    left, top = source_x, source_y
                    right = min(left + 1, n - 1)
                    bottom = min(top + 1, n - 1)
                    raw_tl = self._raw(left, top)
                    raw_tr = self._raw(right, top)
                    raw_bl = self._raw(left, bottom)
                    raw_br = self._raw(right, bottom)
                    off_x = target_x * source_scale - source_x
                    off_y = target_y * source_scale - source_y
                    result[index] = round(
                        _blerp(raw_tl, raw_tr, raw_bl, raw_br, off_x, off_y)
                    )
            self.p_hm_data = result
            self.n_size = 33  # matches AAEmu's effective 33x33 use

    def _raw(self, x: int, y: int) -> int:
        if self.n_size > 0:
            idx = x * self.n_size + y
            if idx < len(self.p_hm_data):
                return self.p_hm_data[idx]
        return 0

    def get_height(self, x: int, y: int) -> float:
        if self.n_size > 0:
            idx = x * self.n_size + y
            if idx < len(self.p_hm_data):
                return self._raw_data_to_height(self.p_hm_data[idx])
        return 0.0

    def _raw_data_to_height(self, data: int) -> float:
        return 0.05 * self._i_offset + (data >> 4) * self._i_step * 0.05


def _lerp(s, e, t):
    return s + (e - s) * t


def _blerp(c00, c10, c01, c11, tx, ty):
    return _lerp(_lerp(c00, c10, tx), _lerp(c01, c11, tx), ty)


class Hmap:
    def __init__(self):
        self.version = 0
        self.chunk_size = 0
        self.heightmap_size_in_units = 0
        self.unit_size_in_meters = 0
        self.sector_size_in_meters = 0
        self.sectors_table_size = 0
        self.heightmap_z_ratio = 0.0
        self.ocean_water_level = 0.0
        self.nodes = []

    def read(self, data: bytes) -> int:
        self.version = data[0]
        (
            self.chunk_size,
            self.heightmap_size_in_units,
            self.unit_size_in_meters,
            self.sector_size_in_meters,
            self.sectors_table_size,
        ) = struct.unpack_from("<5i", data, 4)
        (self.heightmap_z_ratio, self.ocean_water_level) = struct.unpack_from(
            "<2f", data, 24
        )
        pos = 32
        if self.version >= 24:
            pos += 128  # unk

        nodes_read = 0
        while pos != self.chunk_size:
            node = NodeCell()
            try:
                pos = node.read(data, pos)
            except struct.error:
                return -1
            self.nodes.append(node)
            nodes_read += 1
        return nodes_read


def load_heightmap_bytes(data: bytes, name: str = "<bytes>") -> Hmap:
    """Parse a heightmap.dat payload already in memory."""
    hmap = Hmap()
    n = hmap.read(data)
    if n < 0:
        raise ValueError(f"failed to parse heightmap: {name}")
    return hmap


def load_heightmap(path: Path) -> Hmap:
    return load_heightmap_bytes(path.read_bytes(), str(path))


def build_cell_grid(hmap: Hmap, height_max_coefficient: float | None = None):
    """Assemble the 512x512 cell height grid from quadtree nodes.

    Returns dict {width, height, unit_size, max_height, water_level, heights}
    where heights[row][col] are METERS (float) — ready for the 3D editor.
    height_max_coefficient is ignored (kept for API compat); get_height()
    already returns meters.
    """
    sorted_nodes = sorted(
        (n for n in hmap.nodes if n.p_hm_data),
        key=lambda n: (n.box_min[0], n.box_min[1]),
    )
    width = CELL_HMAP_RESOLUTION
    heights = [[0.0] * width for _ in range(width)]

    for sector_x in range(SECTORS_PER_CELL):
        for sector_y in range(SECTORS_PER_CELL):
            node = sorted_nodes[sector_x * SECTORS_PER_CELL + sector_y]
            for unit_x in range(SECTOR_HMAP_RESOLUTION):
                for unit_y in range(SECTOR_HMAP_RESOLUTION):
                    heights[sector_x * SECTOR_HMAP_RESOLUTION + unit_x][
                        sector_y * SECTOR_HMAP_RESOLUTION + unit_y
                    ] = node.get_height(unit_x, unit_y)

    return {
        "width": width,
        "height": width,
        "unit_size": hmap.unit_size_in_meters,
        "max_height": 4096.0,
        "water_level": hmap.ocean_water_level,
        "heights": heights,
    }


def build_overview_grid(hmap: Hmap, res: int = 16) -> dict:
    """One height sample per terrain sector (default 16×16, 64 m)."""
    sorted_nodes = sorted(
        (n for n in hmap.nodes if n.p_hm_data),
        key=lambda n: (n.box_min[0], n.box_min[1]),
    )
    res = max(1, min(res, SECTORS_PER_CELL))
    step = SECTORS_PER_CELL // res
    heights = []
    lo, hi = 1e9, -1e9
    for sx in range(res):
        row = []
        for sy in range(res):
            idx = (sx * step) * SECTORS_PER_CELL + (sy * step)
            if idx >= len(sorted_nodes):
                h = 0.0
            else:
                node = sorted_nodes[idx]
                mid = max(0, node.n_size // 2)
                h = node.get_height(mid, mid)
            lo = min(lo, h)
            hi = max(hi, h)
            row.append(round(h, 2))
        heights.append(row)
    return {
        "width": res,
        "unit_size": CELL_SIZE / res,
        "water_level": hmap.ocean_water_level,
        "min": round(lo, 2) if lo < 1e8 else 0.0,
        "max": round(hi, 2) if hi > -1e8 else 0.0,
        "heights": heights,
    }


def default_height_max_coefficient(max_height: float = 4096.0) -> float:
    """AAEmu: ushort.MaxValue / (maxTerrainHeight / 4.0)."""
    return 65535.0 / (max_height / 4.0)


def write_obj(grid: dict, out_path: Path, scale: float = 1.0):
    """Write a Wavefront OBJ terrain mesh (x=col, y=row, z=height)."""
    w = grid["width"]
    h = grid["height"]
    heights = grid["heights"]
    coeff = default_height_max_coefficient(grid["max_height"])

    lines = ["# ArcheAge terrain mesh"]
    lines.append(
        f"# {w}x{h} grid, unit {grid['unit_size']} m, water {grid['water_level']}"
    )
    for row in range(h):
        for col in range(w):
            z = heights[row][col] / coeff
            lines.append(f"v {col * scale} {row * scale} {z:.3f}")
    for row in range(h - 1):
        for col in range(w - 1):
            a = row * w + col + 1
            b = a + 1
            c = a + w
            d = c + 1
            lines.append(f"f {a} {b} {d}")
            lines.append(f"f {a} {d} {c}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    path = Path(sys.argv[1])
    hmap = load_heightmap(path)
    print(
        f"version={hmap.version} chunk={hmap.chunk_size} "
        f"hmap={hmap.heightmap_size_in_units} unit={hmap.unit_size_in_meters} "
        f"sector={hmap.sector_size_in_meters} zratio={hmap.heightmap_z_ratio} "
        f"ocean={hmap.ocean_water_level} nodes={len(hmap.nodes)}"
    )
