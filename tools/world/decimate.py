"""Vertex-cluster decimation that preserves subset (material) grouping.

Used to shrink composed NPC meshes (body+face+hair+gear) from ~11k verts /
16 materials to a budget that keeps the editor at 60 fps: triangles are
regrouped by their resolved texture first, so the client draws one group per
distinct texture instead of one per equipment slot.
"""

from __future__ import annotations

import numpy as np


def merge_groups_by_key(indices, groups, keys):
    """groups: [(first, count), ...] parallel to keys; returns merged
    (indices, groups, keys) where same-key groups are concatenated."""
    idx = np.asarray(indices, dtype=np.int64).ravel()
    buckets: dict = {}
    order: list = []
    for (first, count), k in zip(groups, keys):
        n = count - (count % 3)
        t = idx[first : first + n].reshape(-1, 3)
        if k not in buckets:
            buckets[k] = []
            order.append(k)
        buckets[k].append(t)
    out = []
    new_groups = []
    new_keys = []
    pos = 0
    for k in order:
        t = np.concatenate(buckets[k])
        out.append(t)
        new_groups.append((pos, len(t) * 3))
        new_keys.append(k)
        pos += len(t) * 3
    out_idx = np.concatenate(out).ravel() if out else np.zeros(0, np.int64)
    return out_idx, new_groups, new_keys


def decimate(positions, normals, uvs, indices, groups, keys, target_verts=2600):
    """positions: flat [x,y,z]*, normals same, uvs [u,v]*, indices flat,
    groups [(first,count)] over indices, keys parallel material identity.

    Returns dict with flat python lists ready for the model JSON.
    """
    pos = np.asarray(positions, dtype=np.float64).reshape(-1, 3)
    nrm = np.asarray(normals, dtype=np.float64).reshape(-1, 3) if len(normals) else None
    uv = np.asarray(uvs, dtype=np.float64).reshape(-1, 2) if len(uvs) else None
    idx = np.asarray(indices, dtype=np.int64).ravel()

    # regroup by texture key first
    idx, groups, keys = merge_groups_by_key(idx, groups, keys)

    n = len(pos)
    if n <= target_verts:
        return _emit(pos, nrm, uv, idx, groups, keys)

    mn = pos.min(axis=0)
    span = np.maximum(pos.max(axis=0) - mn, 1e-6)

    def _cluster(g):
        grid = np.floor((pos - mn) / (span * g)).astype(np.int64)
        dims = np.maximum(grid.max(axis=0) + 1, 1)
        code = (grid[:, 0] * dims[1] + grid[:, 1]) * dims[2] + grid[:, 2]
        return np.unique(code, return_inverse=True)

    # surface meshes cluster by area, not volume: binary-search the cell
    # fraction that lands just under the vertex budget
    lo, hi = 1e-4, 1.0
    for _ in range(14):
        mid = (lo * hi) ** 0.5
        if len(_cluster(mid)[0]) > target_verts:
            lo = mid
        else:
            hi = mid
    uniq, remap = _cluster(hi)

    m = len(uniq)
    newpos = np.zeros((m, 3))
    counts = np.bincount(remap, minlength=m)
    for ax in range(3):
        newpos[:, ax] = np.bincount(remap, weights=pos[:, ax], minlength=m) / counts
    newnrm = None
    if nrm is not None:
        newnrm = np.zeros((m, 3))
        for ax in range(3):
            newnrm[:, ax] = np.bincount(remap, weights=nrm[:, ax], minlength=m) / counts
        ln = np.maximum(np.linalg.norm(newnrm, axis=1), 1e-6)
        newnrm /= ln[:, None]
    newuv = None
    if uv is not None:
        # representative uv = first vertex of the cluster (averaging seams smears textures)
        first = np.full(m, -1, dtype=np.int64)
        order = np.argsort(remap, kind="stable")
        uniq2, starts = np.unique(remap[order], return_index=True)
        first[uniq2] = order[starts]
        newuv = uv[first]

    tri = idx.reshape(-1, 3)
    new_tri = remap[tri]
    keep = (new_tri[:, 0] != new_tri[:, 1]) & (new_tri[:, 1] != new_tri[:, 2]) & (new_tri[:, 0] != new_tri[:, 2])

    out_groups = []
    out_keys = []
    parts = []
    pos_acc = 0
    for (first_i, count), k in zip(groups, keys):
        ntri = count - (count % 3)
        t = new_tri[first_i // 3 : first_i // 3 + ntri // 3]
        kk = keep[first_i // 3 : first_i // 3 + ntri // 3]
        t = t[kk]
        if len(t) == 0:
            continue
        parts.append(t)
        out_groups.append((pos_acc, len(t) * 3))
        pos_acc += len(t) * 3
        out_keys.append(k)
    out_idx = np.concatenate(parts).ravel() if parts else np.zeros(0, np.int64)
    return _emit(newpos, newnrm, newuv, out_idx, out_groups, out_keys)


def _emit(pos, nrm, uv, idx, groups, keys):
    return {
        "positions": [round(float(v), 3) for v in pos.ravel()],
        "normals": [round(float(v), 4) for v in (nrm if nrm is not None else np.zeros_like(pos)).ravel()],
        "uvs": [round(float(v), 5) for v in (uv if uv is not None else np.zeros((len(pos), 2))).ravel()],
        "indices": [int(v) for v in idx],
        "groups": groups,
        "keys": keys,
    }
