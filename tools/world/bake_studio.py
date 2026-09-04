#!/usr/bin/env python3
"""Bake game_pak meshes + terrain textures for ArcheaAge Editor.

  python tools/world/bake_studio.py --pak <game_pak> --world arche_mall_world \
      --out apps/studio/ui/cache
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.pak import PakIndex, open_pak  # noqa: E402

from tools.world.cgf import parse_cgf  # noqa: E402
from tools.world.entities import parse_entities_text  # noqa: E402
from tools.world.heightmap import (  # noqa: E402
    build_cell_grid,
    build_overview_grid,
    load_heightmap_bytes,
)
from tools.world.mtl import best_folder_mtl, mtl_candidates, parse_mtl  # noqa: E402
from tools.world.objects_dat import matrix_to_three, parse_objects_dat
from tools.world.brush import attach_names, parse_brush_dat
from tools.world.chr import parse_chr  # noqa: E402
from tools.world.vegetation import (  # noqa: E402
    parse_vegetation_dat,
    parse_vegetation_xml,
)

TERRAIN_FALLBACKS = [
    "game/textures/aa_terrain/field/tr_field_grass_623b_df.dds",
    "game/textures/aa_terrain/field/tr_field_dirt_230c_df.dds",
    "game/textures/aa_terrain/field/tr_field_dirt_624a_df.dds",
    "game/textures/aa_terrain/wet/tr_beach_coral_201a_df.dds",
    "game/textures/aa_terrain/canyon/tr_canyon_rock3d_230e_df.dds",
]


def _id(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def dds_to_png(data: bytes, dest: Path) -> bool:
    try:
        from PIL import Image
    except ImportError:
        print("Pillow is required: pip install pillow")
        return False
    try:
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGBA")
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, "PNG")
        return True
    except Exception as e:
        print("  dds fail", dest.name, e)
        return False


def bake_texture(idx: PakIndex, dds_path: str, out: Path, cache: dict) -> str | None:
    if not dds_path:
        return None
    key = dds_path.replace("\\", "/").lower()
    if key in cache:
        return cache[key]
    raw = idx.read(dds_path)
    if not raw:
        cache[key] = None
        return None
    rel = "tex/" + _id(key) + ".png"
    dest = out / rel
    if not dest.exists() and not dds_to_png(raw, dest):
        cache[key] = None
        return None
    cache[key] = rel
    return rel


def index_mtls(idx: PakIndex) -> dict[str, list[str]]:
    folders: dict[str, list[str]] = {}
    for low, orig in idx.lower.items():
        if low.endswith(".mtl"):
            folder = low.rsplit("/", 1)[0]
            folders.setdefault(folder, []).append(orig)
    return folders


def resolve_mtl(
    idx: PakIndex,
    model: str,
    mtl_cache: dict,
    folder_mtls: dict[str, list[str]],
    mtl_names: list[str] | None = None,
) -> dict[str, dict]:
    cache_key = model
    if cache_key in mtl_cache:
        return mtl_cache[cache_key]
    parsed: dict[str, dict] = {}

    def add(raw: bytes) -> None:
        parsed.update(parse_mtl(raw.decode("utf-8", "replace")))

    folder = model.replace("\\", "/").rsplit("/", 1)[0]
    names = [n for n in (mtl_names or []) if n]
    # The CGF MtlName list's first entry is usually the material-library file
    # name (e.g. "verdura_house_flower_shop" for verdura_house_garden_c.cgf).
    lib_cands: list[str] = []
    for n in names[:1] + names:
        base = n.replace("\\", "/").rsplit("/", 1)[-1]
        if not base:
            continue
        lib_cands += [
            folder + "/" + base + ".mtl",
            base + ".mtl",
            "game/materials/" + base + ".mtl",
        ]

    for cand in mtl_candidates(model) + lib_cands:
        raw = idx.read(cand)
        if raw:
            add(raw)
            if parsed:
                mtl_cache[cache_key] = parsed
                return parsed

    for name in names:
        base = name.replace("\\", "/").rsplit("/", 1)[-1]
        if not base:
            continue
        for cand in (folder + "/" + base + ".mtl", base + ".mtl"):
            raw = idx.read(cand)
            if raw:
                add(raw)
                if parsed:
                    mtl_cache[cache_key] = parsed
                    return parsed

    hit = best_folder_mtl(model, folder_mtls.get(folder.lower(), []))
    if hit:
        raw = idx.read(hit)
        if raw:
            add(raw)
    mtl_cache[cache_key] = parsed
    return parsed


def bake_model(
    idx: PakIndex,
    model: str,
    out: Path,
    tex_cache: dict,
    mtl_cache: dict,
    mesh_cache: dict,
    folder_mtls: dict,
    parser=None,
) -> str | None:
    parser = parser or parse_cgf
    key = model.replace("\\", "/").lower()
    if key in mesh_cache:
        return mesh_cache[key]
    rel = "models/" + _id(key) + ".json"
    dest = out / rel
    if dest.exists():
        mesh_cache[key] = rel
        return rel
    raw = idx.read(model)
    if not raw:
        mesh_cache[key] = None
        return None
    mesh = parser(raw)
    if not mesh:
        mesh_cache[key] = None
        return None
    mats = resolve_mtl(
        idx, model, mtl_cache, folder_mtls, mesh.get("materials")
    )
    # The CGF MtlName list holds DCC-side names ("wall01", "Material #29")
    # that usually DON'T match the .mtl SubMaterial names ("wood", "ivy"...).
    # Both lists are exporter-generated, so matId indexes the .mtl
    # SubMaterials in file order. Mapping by name alone produced NONE →
    # everything fell back to the first diffuse → stretched/wrong textures.
    names = mesh.get("materials") or []
    children = names[1:] if len(names) > 1 else names
    mtl_subs = list(mats.values())
    diffuse_subs = [v for v in mtl_subs if v.get("diffuse")]
    for s in mesh["subsets"]:
        mid = int(s.get("matId") or 0)
        info = mats.get(s["mat"]) or {}
        if not info.get("diffuse") and 0 <= mid < len(mtl_subs):
            info = mtl_subs[mid] or {}
        if not info.get("diffuse") and 0 <= mid < len(children):
            info = mats.get(children[mid]) or {}
        if not info.get("diffuse") and len(diffuse_subs) == 1:
            info = diffuse_subs[0]
        dds = (info or {}).get("diffuse") or ""
        png = bake_texture(idx, dds, out, tex_cache) if dds else None
        s["texture"] = png
        s["alphaTest"] = float((info or {}).get("alphaTest") or 0)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(mesh, separators=(",", ":")), encoding="utf-8")
    mesh_cache[key] = rel
    print("  mesh", model.split("/")[-1], "->", rel, "sub", len(mesh["subsets"]))
    return rel


def _bake_composed(composed, uid, idx, out, tex_cache, mtl_cache, folder_mtls):
    """Write an already-composed NPC mesh (parts carry 'part' source paths).

    Subsets are merged by resolved texture and the mesh is decimated to a
    vertex budget: a composed NPC used to be 16 material groups × 11k verts,
    which made characters the single biggest draw-call / triangle source in
    the editor.
    """
    from tools.world.decimate import decimate

    rel = "models/npc_" + str(uid) + ".json"
    dest = out / rel
    if dest.exists():
        return rel
    groups = []
    keys = []
    reps = []
    for s in composed.get("subsets") or []:
        if not s.get("indexCount"):
            continue
        part = s.get("part") or ""
        info = {}
        if part:
            mats = resolve_mtl(idx, part, mtl_cache, folder_mtls, [s.get("mat")])
            info = mats.get(s.get("mat")) or {}
            if not info.get("diffuse"):
                subs = list(mats.values())
                dif = [v for v in subs if v.get("diffuse")]
                if dif:
                    info = dif[0]
        dds = info.get("diffuse") or ""
        png = bake_texture(idx, dds, out, tex_cache) if dds else None
        alpha = float(info.get("alphaTest") or 0)
        groups.append((int(s.get("firstIndex") or 0), int(s.get("indexCount") or 0)))
        keys.append((png or "", alpha > 0))
        reps.append(s)
    if not groups:
        return None
    rep_by_key: dict = {}
    for k, s in zip(keys, reps):
        rep_by_key.setdefault(k, s)
    out_mesh = decimate(
        composed.get("positions") or [],
        composed.get("normals") or [],
        composed.get("uvs") or [],
        composed.get("indices") or [],
        groups,
        keys,
        target_verts=1400,
    )
    subsets = []
    for (first, count), (png, cut) in zip(out_mesh["groups"], out_mesh["keys"]):
        src = rep_by_key[(png, cut)]
        subsets.append(
            {
                "firstIndex": first,
                "indexCount": count,
                "mat": src.get("mat") or "",
                "matId": src.get("matId") or 0,
                "part": src.get("part") or "",
                "texture": png or None,
                "alphaTest": float(src.get("alphaTest") or 0) if cut else 0,
            }
        )
    mesh = {
        "positions": out_mesh["positions"],
        "normals": out_mesh["normals"],
        "uvs": out_mesh["uvs"],
        "indices": out_mesh["indices"],
        "subsets": subsets,
        "materials": composed.get("materials") or [""],
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(mesh, separators=(",", ":")), encoding="utf-8")
    return rel


def bake_terrain(idx: PakIndex, out: Path, tex_cache: dict) -> dict:
    layers = {}
    for dds in TERRAIN_FALLBACKS:
        png = bake_texture(idx, dds, out, tex_cache)
        if png:
            name = dds.split("/")[-1].replace("_df.dds", "")
            if "grass" in name:
                layers.setdefault("grass", png)
            elif "dirt" in name:
                layers.setdefault("dirt", png)
            elif "coral" in name or "sand" in name or "beach" in name:
                layers.setdefault("sand", png)
            elif "rock" in name or "canyon" in name:
                layers.setdefault("rock", png)
    return layers


def load_veg_groups(idx: PakIndex, world: str, cache: dict) -> dict:
    if world in cache:
        return cache[world]
    raw = idx.read(f"game/worlds/{world}/vegetation.xml")
    groups = parse_vegetation_xml(raw.decode("utf-8", "replace")) if raw else {}
    cache[world] = groups
    print(f"  vegetation groups {len(groups)}")
    return groups


def _load_jsonc(path: Path):
    """AAEmu spawn files are JSONC (// comments, optional trailing commas)."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return json.loads(text)


def load_npc_meta(db_path: Path | None) -> dict:
    """UnitId -> {name, aggr, grade, model} from the client's compact.sqlite3."""
    if not db_path or not db_path.exists():
        return {}
    try:
        import sqlite3

        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = con.cursor()
        files = {}
        try:
            for mid, f in cur.execute("select id, model_file from actor_models"):
                files[mid] = f
        except Exception:
            pass
        meta = {}
        q = "select id, name, aggression, npc_grade_id, npc_kind_id, model_id from npcs"
        for nid, name, aggr, grade, kind, model_id in cur.execute(q):
            meta[nid] = {
                "name": name or "",
                "aggr": 1 if aggr == "t" else 0,
                "grade": int(grade or 1),
                "kind": int(kind or 1),
                "model": files.get(model_id) or "",
            }
        con.close()
        print(f"  npc meta loaded: {len(meta)}")
        return meta
    except Exception as e:
        print("  npc meta fail:", e)
        return {}


def _chr_from_cdf(idx: PakIndex, path: str) -> str | None:
    """Resolve a character model path (.cdf or .chr) to a real body .chr."""
    p = path.replace("\\", "/").lstrip("/")
    if not p.lower().startswith("game/"):
        p = "game/" + p
    low = p.lower()
    if low.endswith(".chr"):
        return p
    if not low.endswith(".cdf"):
        return None
    raw = idx.read(p)
    if not raw:
        return None
    import re

    m = re.search(r'<Model\s+File="([^"]+)"', raw.decode("utf-8", "replace"), re.I)
    if not m:
        return None
    base = m.group(1).replace("\\", "/")
    if not base.lower().startswith("game/"):
        base = "game/" + base.lstrip("/")
    # *_base.chr are skeleton stubs; the real body is the sibling *_nude.chr
    cands = [base]
    low_b = base.lower()
    if low_b.endswith("_base.chr"):
        cands.append(base[:-9] + "_nude.chr")
    else:
        stem = base[:-4] if low_b.endswith(".chr") else base
        cands.append(stem + "_nude.chr")
    from tools.world.chr import parse_chr

    for c in cands:
        d = idx.read(c)
        if d and parse_chr(d):
            if len((parse_chr(d) or {}).get("positions") or []) > 150:
                return c
    return cands[-1] if idx.read(cands[-1]) else cands[0]


def load_world_spawns(world: str, spawns_dir: Path | None, npc_meta: dict | None = None) -> tuple[list, list]:
    if not spawns_dir:
        return [], []
    folder = spawns_dir / world
    npcs, doodads = [], []
    npc_p = folder / "npc_spawns.json"
    dd_p = folder / "doodad_spawns.json"
    if npc_p.exists():
        try:
            npcs = _load_jsonc(npc_p)
        except Exception as e:
            print("  npc_spawns parse fail", e)
            npcs = []
    if dd_p.exists():
        try:
            doodads = _load_jsonc(dd_p)
        except Exception as e:
            print("  doodad_spawns parse fail", e)
            doodads = []
    if npc_meta:
        for it in npcs:
            m = npc_meta.get(it.get("UnitId"))
            if m:
                it["_meta"] = m
    print(f"  spawn tables npcs={len(npcs)} doodads={len(doodads)}")
    return npcs, doodads


def _cell_of(x: float, y: float) -> str:
    return f"{int(x // 1024):03d}_{int(y // 1024):03d}"


def filter_spawns(items: list, cell: str, cap: int) -> list:
    out = []
    for it in items:
        pos = it.get("Position") or {}
        x, y, z = pos.get("X"), pos.get("Y"), pos.get("Z")
        if x is None or y is None:
            continue
        if _cell_of(float(x), float(y)) != cell:
            continue
        rec = {
            "unitId": it.get("UnitId") or 0,
            "pos": [round(float(x), 2), round(float(y), 2), round(float(z or 0), 2)],
            "yaw": round(float(pos.get("Yaw") or 0), 2),
        }
        if it.get("Title"):
            rec["title"] = it["Title"]
        m = it.get("_meta")
        if m:
            rec["name"] = m.get("name") or ""
            rec["aggr"] = m.get("aggr", 0)
            rec["grade"] = m.get("grade", 1)
            rec["model"] = m.get("model") or ""
        out.append(rec)
        if len(out) >= cap:
            break
    return out


def bake_cell(idx: PakIndex, world: str, cell: str, out: Path, caches: dict) -> dict:
    obj_name = f"game/worlds/{world}/cells/{cell}/client/object.dat"
    ent_name = f"game/worlds/{world}/cells/{cell}/client/entities.xml"
    objects = []
    raw = idx.read(obj_name)
    if raw:
        parsed = parse_objects_dat(raw)
        print(f"  {cell} assets={len(parsed['assets'])} brushes={len(parsed['brushes'])}")
        for b in parsed["brushes"]:
            path = b["path"].replace("\\", "/").lower()
            if path.endswith("/box.cgf") or path.endswith("helper") or "nodraw" in path:
                continue
            rel = bake_model(
                idx,
                b["path"],
                out,
                caches["tex"],
                caches["mtl"],
                caches["mesh"],
                caches["folders"],
            )
            if not rel:
                continue
            objects.append(
                {
                    "model": b["path"],
                    "mesh": rel,
                    "matrix": matrix_to_three(b["matrix"]),
                }
            )

    entities = []
    eraw = idx.read(ent_name)
    if eraw:
        for e in parse_entities_text(eraw.decode("utf-8", "replace")):
            if not e.get("model"):
                continue
            rel = bake_model(
                idx,
                e["model"],
                out,
                caches["tex"],
                caches["mtl"],
                caches["mesh"],
                caches["folders"],
            )
            if rel:
                e = dict(e)
                e["mesh"] = rel
                entities.append(e)
        tmp.unlink(missing_ok=True)
    prev_path = out / ("cells/" + world + "_" + cell + "_objects.json")
    prev = None
    if prev_path.exists():
        try:
            prev = json.loads(prev_path.read_text(encoding="utf-8"))
        except Exception:
            prev = None
    heightmap = (prev or {}).get("heightmap") or bake_height(idx, world, cell)

    # ---- drop unsupported floaters ----
    # brush/object entries whose authored Z sits far above OUR heightmap with
    # no neighbouring geometry at that level are props that belonged to terrain
    # features (mountains) the heightmap doesn't carry → they float in the sky.
    if heightmap and objects:
        hs = heightmap.get("heights") or []
        hn = len(hs)
        if hn > 8:
            def _th(x, y):
                ix = min(hn - 1, max(0, int(round(x / 2))))
                iy = min(hn - 1, max(0, int(round(y / 2))))
                row = hs[ix]
                return row[iy] if row and iy < len(row) else 0.0

            G = 40
            occ: dict[tuple[int, int], list[float]] = {}
            for o in objects:
                m = o["matrix"]
                gx = int(m[12] // G)
                gy = int(m[14] // G)
                occ.setdefault((gx, gy), []).append(m[13])

            def _supported(x, y, z, terr):
                if z - terr <= 25:
                    return True
                gx = int(x // G)
                gy = int(y // G)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for hz in occ.get((gx + dx, gy + dy), ()):
                            if terr + 4 < hz <= z + 12:
                                return True
                return False

            before = len(objects)
            objects = [
                o for o in objects
                if _supported(o["matrix"][12], o["matrix"][14], o["matrix"][13],
                              _th(o["matrix"][12], o["matrix"][14]))
            ]
            dropped = before - len(objects)
            if dropped:
                print(f"  {cell} dropped {dropped} unsupported floaters")

    vegetation = []
    veg_raw = idx.read(f"game/worlds/{world}/cells/{cell}/client/vegetation.dat")
    if veg_raw:
        groups = load_veg_groups(idx, world, caches.setdefault("veg_groups", {}))
        inst = parse_vegetation_dat(veg_raw, groups)
        print(f"  {cell} vegetation={len(inst)}")
        for v in inst:
            rel = bake_model(
                idx,
                v["model"],
                out,
                caches["tex"],
                caches["mtl"],
                caches["mesh"],
                caches["folders"],
            )
            if not rel:
                continue
            vegetation.append(
                {
                    "model": v["model"],
                    "name": v["name"],
                    "mesh": rel,
                    "pos": v["pos"],
                    "scale": v["scale"],
                    "yaw": v["yaw"],
                    "span": v["span"],
                }
            )

    npcs_all, doodads_all = caches.get("spawns") or ([], [])
    npcs = filter_spawns(npcs_all, cell, 2000)
    doodads = filter_spawns(doodads_all, cell, 800)

    # ---- NPC models: composite body+head+gear (.chr parts) per UnitId ----
    from tools.world.npcmodel import load_npc_meshes, compose_chr
    import sqlite3 as _sq

    npc_cache = caches.setdefault("npc_models", {})
    con = caches.get("npc_con")
    if con is None and caches.get("db_path"):
        try:
            con = _sq.connect(f"file:{caches['db_path']}?mode=ro", uri=True)
            caches["npc_con"] = con
        except Exception:
            caches["npc_con"] = False
            con = False
    if con:
        for n in npcs:
            uid = n.get("unitId")
            if not uid:
                continue
            if uid in npc_cache:
                if npc_cache[uid]:
                    n["mesh"] = npc_cache[uid]
                continue
            rel = None
            try:
                meshes, kept = load_npc_meshes(idx, con, uid, {})
                if meshes:
                    composed = compose_chr(meshes, [p["path"] for p in kept])
                    rel = _bake_composed(
                        composed, uid, idx, out,
                        caches["tex"], caches["mtl"], caches["folders"],
                    )
            except Exception as e:
                print("  npc model fail", uid, e)
            npc_cache[uid] = rel
            if rel:
                n["mesh"] = rel

    # ---- Doodad models: real .cgf/.chr instead of placeholder cubes ----
    dd_models = caches.get("doodad_models")
    if dd_models is None:
        dd_models = {}
        if caches.get("db_path"):
            try:
                from tools.world.doodadmodel import load_doodad_models

                dd_models = load_doodad_models(Path(caches["db_path"]), idx)
            except Exception as e:
                print("  doodad models fail", e)
        caches["doodad_models"] = dd_models
    if dd_models:
        from tools.world.doodadmodel import is_chr as _dd_is_chr

        for d in doodads:
            path = dd_models.get(d.get("unitId"))
            if not path:
                continue
            parser = parse_chr if _dd_is_chr(path) else None
            rel = bake_model(
                idx, path, out,
                caches["tex"], caches["mtl"], caches.setdefault("dd_mesh", {}),
                caches["folders"], parser=parser,
            )
            if rel:
                d["mesh"] = rel
    if npcs or doodads:
        print(f"  {cell} npcs={len(npcs)} doodads={len(doodads)}")

    return {
        "cell": cell,
        "heightmap": heightmap,
        "objects": objects,
        "entityMeshes": entities,
        "entities": entities,
        "vegetation": vegetation,
        "npcs": npcs,
        "doodads": doodads,
    }


def _decode_dxt1_np(px: bytes, n: int = 128):
    """Vectorised DXT1/BC1 decode -> (n, n, 3) uint8 array."""
    import numpy as np

    a = np.frombuffer(px, dtype=np.uint8).reshape(-1, 8)
    c0 = (a[:, 0].astype(np.uint16) | a[:, 1].astype(np.uint16) << 8)
    c1 = (a[:, 2].astype(np.uint16) | a[:, 3].astype(np.uint16) << 8)

    def unpack565(c):
        r = ((c >> 11) & 31).astype(np.float32) * 255 / 31
        g = ((c >> 5) & 63).astype(np.float32) * 255 / 63
        b = (c & 31).astype(np.float32) * 255 / 31
        return r, g, b

    r0, g0, b0 = unpack565(c0)
    r1, g1, b1 = unpack565(c1)
    cond = c0 > c1
    pal_r = np.stack(
        [r0, r1,
         np.where(cond, (2 * r0 + r1) / 3, (r0 + r1) / 2),
         np.where(cond, (r0 + 2 * r1) / 3, np.zeros_like(r0))],
        axis=1,
    )
    pal_g = np.stack(
        [g0, g1,
         np.where(cond, (2 * g0 + g1) / 3, (g0 + g1) / 2),
         np.where(cond, (g0 + 2 * g1) / 3, np.zeros_like(g0))],
        axis=1,
    )
    pal_b = np.stack(
        [b0, b1,
         np.where(cond, (2 * b0 + b1) / 3, (b0 + b1) / 2),
         np.where(cond, (b0 + 2 * b1) / 3, np.zeros_like(b0))],
        axis=1,
    )
    idx = np.stack(
        [(a[:, 4 + j] >> s) & 3 for j in range(4) for s in (0, 2, 4, 6)],
        axis=1,
    ).reshape(-1, 4, 4)  # [block][row][col] -> palette entry
    # assemble full image: block index = by*(n//4)+bx
    bi = np.arange((n // 4) * (n // 4))
    out = np.zeros((n, n, 3), dtype=np.uint8)
    col_of = bi % (n // 4)
    row_of = bi // (n // 4)
    for py in range(4):
        for px_ in range(4):
            xs = col_of * 4 + px_
            ys = row_of * 4 + py
            sel = idx[:, py, px_]
            out[ys, xs, 0] = pal_r[bi, sel].astype(np.uint8)
            out[ys, xs, 1] = pal_g[bi, sel].astype(np.uint8)
            out[ys, xs, 2] = pal_b[bi, sel].astype(np.uint8)
    return out


def bake_cover(idx: PakIndex, world: str, cell: str, out: Path) -> str | None:
    """Assemble the cell's cover.ctc (baked CryEngine terrain diffuse with the
    real biome/road painting) into a 2048x2048 PNG. This is what gives the
    ground its actual roads/paths instead of procedural noise."""
    from tools.world.coverctc import header as ctc_header
    from tools.world.coverctc import heightmap_nodes

    raw = idx.read(f"game/worlds/{world}/cells/{cell}/client/terrain/cover.ctc")
    hraw = idx.read(f"game/worlds/{world}/cells/{cell}/client/terrain/heightmap.dat")
    if not raw or not hraw:
        return None
    rel = f"terrain/{world}_{cell}.png"
    dest = out / rel
    if dest.exists():
        return rel
    try:
        from PIL import Image
        import numpy as np

        h = ctc_header(raw)
        nodes = heightmap_nodes(hraw)
        if len(nodes) != h["n_nodes"]:
            return None
        x0 = min(nd["box_min"][0] for nd in nodes)
        y0 = min(nd["box_min"][1] for nd in nodes)
        span = max(
            max(nd["box_max"][0] for nd in nodes) - x0,
            max(nd["box_max"][1] for nd in nodes) - y0,
        )
        if span <= 0:
            return None
        w = int(round(span / 64.0 * 128))
        img = np.zeros((w, w, 3), dtype=np.uint8)
        off = h["payload_off"]
        for k, nd in enumerate(nodes):
            if nd["nsize"] != 33:
                continue
            sx = int(round((nd["box_min"][0] - x0) / 64.0 * 128))
            sy = int(round((nd["box_min"][1] - y0) / 64.0 * 128))
            if sx + 128 > w or sy + 128 > w:
                continue
            a = _decode_dxt1_np(raw[off + k * 8192 : off + (k + 1) * 8192])
            # stored image row = world +X; assembled map is [row=+Y, col=+X]
            img[sy : sy + 128, sx : sx + 128] = a.transpose(1, 0, 2)
        dest.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(img).save(dest, "PNG", optimize=False)
        return rel
    except Exception as e:
        print("  cover fail", cell, e)
        return None


def bake_height(idx: PakIndex, world: str, cell: str) -> dict | None:
    name = f"game/worlds/{world}/cells/{cell}/client/terrain/heightmap.dat"
    raw = idx.read(name)
    if not raw:
        return None
    try:
        return build_cell_grid(load_heightmap_bytes(raw, name))
    except Exception as e:
        print("  heightmap fail", cell, e)
        return None


def bake_overview(idx: PakIndex, world: str, out: Path, cells: list[str]) -> str:
    items = []
    for i, cell in enumerate(cells):
        if i % 40 == 0:
            print(f"  overview {i}/{len(cells)} {cell}")
        grid = bake_overview_cell(idx, world, cell)
        if not grid:
            continue
        items.append({"id": cell, **grid})
    rel = f"overview_{world}.json"
    dest = out / rel
    dest.write_text(
        json.dumps(
            {"world": world, "res": 16, "cellSize": 1024, "cells": items},
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print("wrote", rel, "cells", len(items))
    return rel


def bake_overview_cell(idx: PakIndex, world: str, cell: str) -> dict | None:
    name = f"game/worlds/{world}/cells/{cell}/client/terrain/heightmap.dat"
    raw = idx.read(name)
    if not raw:
        return None
    try:
        return build_overview_grid(load_heightmap_bytes(raw, name), 16)
    except Exception as e:
        print("  overview fail", cell, e)
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pak", required=True)
    ap.add_argument("--world", required=True)
    ap.add_argument("--cells", nargs="*", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--spawns",
        default="servers/aaemu/AAEmu.Game/Data/Worlds",
        help="AAEmu Worlds folder with npc_spawns.json / doodad_spawns.json",
    )
    ap.add_argument(
        "--db",
        default=".client_files/ArcheAge 1.2 (r208022) for AAEmu/compact.sqlite3",
        help="client compact.sqlite3 for npc names/aggression (optional)",
    )
    ap.add_argument(
        "--overview",
        action="store_true",
        help="Bake coarse heightmaps for every cell (continent silhouette)",
    )
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("opening pak…")
    idx = PakIndex(open_pak(args.pak))
    prefix = f"game/worlds/{args.world}/cells/"
    found = []
    for n in idx.pak.entries:
        ln = n.lower().replace("\\", "/")
        if ln.startswith(prefix) and ln.endswith("client/object.dat"):
            found.append(n.replace("\\", "/").split("/cells/")[1].split("/")[0])
    all_cells = sorted(set(found))
    # --overview without --cells = continent heights only, no 1200-cell mesh bake
    detail_cells = args.cells if args.cells else ([] if args.overview else all_cells)
    print("detail cells", detail_cells or "(none)", "world cells", len(all_cells))

    caches = {
        "tex": {},
        "mtl": {},
        "mesh": {},
        "folders": index_mtls(idx),
        "veg_groups": {},
    }
    spawns_dir = Path(args.spawns) if args.spawns else None
    if spawns_dir and not spawns_dir.is_absolute():
        spawns_dir = Path.cwd() / spawns_dir
    db_path = Path(args.db) if args.db else None
    if db_path and not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    caches["db_path"] = str(db_path) if db_path and db_path.exists() else None
    caches["npc_meta"] = load_npc_meta(db_path)
    caches["spawns"] = load_world_spawns(args.world, spawns_dir if spawns_dir and spawns_dir.exists() else None, caches.get("npc_meta"))

    terrain = bake_terrain(idx, out, caches["tex"]) if detail_cells else None
    print("terrain layers", terrain)

    overview_rel = None
    if args.overview:
        print("overview", len(all_cells), "cells")
        overview_rel = bake_overview(idx, args.world, out, all_cells)

    cell_out = []
    for cell in detail_cells:
        print("cell", cell)
        info = bake_cell(idx, args.world, cell, out, caches)
        cover = bake_cover(idx, args.world, cell, out)
        rel = "cells/" + args.world + "_" + cell + "_objects.json"
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(info, separators=(",", ":")), encoding="utf-8")
        cell_out.append(
            {
                "id": cell,
                "objects": rel,
                "cover": cover,
                "count": len(info["objects"]),
                "veg": len(info.get("vegetation") or []),
                "npcs": len(info.get("npcs") or []),
            }
        )
        print(
            "  wrote",
            rel,
            "objects",
            len(info["objects"]),
            "veg",
            len(info.get("vegetation") or []),
            "npcs",
            len(info.get("npcs") or []),
        )

    prev = {}
    man_path = out / "manifest.json"
    if man_path.exists():
        try:
            prev = json.loads(man_path.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    # incremental bakes must not drop previously baked cells from the manifest
    prev_cells: list = []
    for w in prev.get("worlds") or []:
        if w.get("id") == args.world:
            prev_cells = w.get("cells") or []
            break
    if not prev_cells:
        prev_cells = prev.get("cells") or []
    merged: dict = {c["id"]: c for c in prev_cells if isinstance(c, dict) and c.get("id")}
    for c in cell_out:
        merged[c["id"]] = c
    cell_out = [merged[k] for k in sorted(merged)]
    entry = {
        "id": args.world,
        "cells": cell_out,
        "overview": overview_rel or prev.get("overview"),
        "models": sum(1 for v in caches["mesh"].values() if v)
        or prev.get("models")
        or 0,
        "textures": sum(1 for v in caches["tex"].values() if v)
        or prev.get("textures")
        or 0,
    }
    worlds = [w for w in prev.get("worlds", []) if w.get("id") != args.world]
    worlds.insert(0, entry)
    manifest = {
        "world": args.world,
        "terrain": terrain or prev.get("terrain"),
        "cells": cell_out,
        "overview": entry["overview"],
        "worlds": worlds,
        "models": entry["models"],
        "textures": entry["textures"],
    }
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("manifest", {k: manifest[k] for k in manifest if k != "worlds"})
    idx.pak.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
