"""NPC gear-composite pipeline: sqlite equip chain -> list of .chr models -> one mesh.

Baking only ``npcs.model_id``'s body .chr renders NPCs as bare nudes; the real
look is body + face + hair + per-slot gear, chained through compact.sqlite3:

  npcs.model_id          -> actor_models.model_file (.cdf)          -> body .chr
  npcs.equip_bodies_id   -> equip_pack_body_parts.{model,face,hair,beard}_id
  npcs.total_custom_id   -> total_character_customs.{model_id,hair_id}
  npcs.equip_cloths_id   -> equip_pack_cloths.{headgear,shirt,pants,glove,
                            shoes,belt,back,cosplay,undershirt,underpants}_id
                            -> items.id -> item_armors.asset_id
  npcs.equip_weapons_id  -> equip_pack_weapons.{mainhand,offhand,ranged}_id
                            -> items.id -> item_weapons.asset_id

Armor asset_id -> armor_assets.id -> item_armor_assets.armor_asset_id ->
item_assets.id (one variant per race "look"); the variant whose
``item_assets.model_id`` matches the ``models`` row named ``<race>_<sex>``
(e.g. nuian_female = 11, ferre_male = 20) is the mesh for this NPC's body.
Hair/face items -> item_body_parts.asset_id -> item_assets.path.
Weapons asset_id -> item_assets.id directly.

``item_assets.path`` is either a real pak file (.chr/.cgf/.cdf), a legacy path
that was re-organized into game/objects/characters/<race>/<sex>/parts/<slot>/
<mat>/<slot_matNNN>/<stem>.cdf (resolve: strip trailing _co01/_rope variant
tokens, find the .cdf by basename, read its <Model File="..."> ->
parts/<slot>/obj/<combined>.chr), or stale (asset removed from the pak —
e.g. npc 502's "c_495" set exists, but npc 230-style "leather007" sets do
not); unresolvable paths are dropped.

Every returned path is verified: idx.read() succeeds and
parse_chr/parse_cgf yields > 50 vertices.

compose_chr() concatenates parsed meshes (same dict shape as parse_chr) in
bind pose — all humanoids share the skeleton, so plain vertex/index offsetting
is correct for a static editor view; per-subset material names and the source
model path survive so textures still resolve per part.

Self-test:  python tools/world/npcmodel.py --self-test
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.pak import PakIndex, open_pak
from tools.world.cgf import parse_cgf
from tools.world.chr import parse_chr

# equip_pack_cloths columns -> label, in compositing (draw) order.
CLOTH_SLOTS = (
    ("undershirt_id", "undershirt"),
    ("underpants_id", "underpants"),
    ("shirt_id", "chest"),
    ("pants_id", "legs"),
    ("belt_id", "belt"),
    ("glove_id", "gloves"),
    ("shoes_id", "feet"),
    ("back_id", "back"),
    ("cosplay_id", "cosplay"),
    ("headgear_id", "head"),
)
WEAPON_SLOTS = (("mainhand_id", "mainhand"), ("offhand_id", "offhand"), ("ranged_id", "ranged"))

_HUMAN_BODY = re.compile(r"/characters/([a-z_]+)/(male|female)/", re.IGNORECASE)
_MODEL_REF = re.compile(rb'<Model\s+File="([^"]+)"', re.IGNORECASE)
_MIN_VERTS = 50

# pak listing of every character/gear model dir (built once per PakIndex)
_INDEX_DIRS = ("game/objects/characters/", "game/objects/item/", "game/objects/env/")


def _game_path(path: str) -> str:
    p = (path or "").replace("\\", "/").lstrip("/")
    return p if p.lower().startswith("game/") else "game/" + p


def _model_verts(data: bytes) -> int:
    mesh = parse_chr(data)
    if not mesh:
        mesh = parse_cgf(data)
    return len((mesh or {}).get("positions") or []) // 3


def _parse_any(data: bytes) -> dict | None:
    return parse_chr(data) or parse_cgf(data)


def _connect(sqlite_path_or_con, cache: dict):
    """Accept a path or an open sqlite3 connection; paths are opened ro+cached."""
    if isinstance(sqlite_path_or_con, sqlite3.Connection):
        return sqlite_path_or_con
    key = "_con"
    if key not in cache:
        p = Path(str(sqlite_path_or_con)).resolve().as_posix()
        cache[key] = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    return cache[key]


def _rows(con, sql: str, args: tuple = ()) -> list:
    try:
        return list(con.execute(sql, args))
    except Exception:
        return []


def _scalar(con, sql: str, args: tuple = ()):
    r = _rows(con, sql, args)
    return r[0][0] if r and r[0] else None


def _base_index(idx: PakIndex, cache: dict) -> dict[str, list[str]]:
    """basename -> [pak paths] for character/item models, built once."""
    bi = cache.get("_base_index")
    if bi is None:
        bi = {}
        for low in idx.lower:
            if low.startswith(_INDEX_DIRS) and low.endswith((".chr", ".cdf", ".cgf")):
                bi.setdefault(low.rsplit("/", 1)[1], []).append(low)
        cache["_base_index"] = bi
    return bi


def _cdf_to_chr(idx: PakIndex, cache: dict, path: str) -> str | None:
    """Read a .cdf's <Model File="..."> and return the (existing) .chr it names."""
    g = _game_path(path)
    hit = cache.get("_cdf", {}).get(g)
    if hit is not None:
        return hit or None
    raw = idx.read(g)
    out = None
    if raw:
        m = _MODEL_REF.search(raw)
        if m:
            cand = _game_path(m.group(1).decode("utf-8", "replace"))
            if idx.get(cand) and _model_verts(idx.read(cand) or b"") > _MIN_VERTS:
                out = cand
    cache.setdefault("_cdf", {})[g] = out or ""
    return out


def _cdf_model_file(idx: PakIndex, path: str) -> str | None:
    """Raw <Model File="..."> target of a .cdf, no vertex validation."""
    raw = idx.read(_game_path(path))
    if not raw:
        return None
    m = _MODEL_REF.search(raw)
    return _game_path(m.group(1).decode("utf-8", "replace")) if m else None


def _body_chr(idx: PakIndex, cache: dict, model_file: str) -> str | None:
    """actor_models.model_file (.cdf/.chr) -> real bind-pose body .chr.

    *_base.chr are skeleton stubs; the skinned body lives in the sibling
    *_nude.chr (same rule as bake_studio._chr_from_cdf).
    """
    if not model_file:
        return None
    p = _game_path(model_file)
    if p.lower().endswith(".cdf"):
        p = _cdf_model_file(idx, p) or p[:-4] + ".chr"
    if not idx.get(p):
        return None
    low = p.lower()
    cands = [p]
    if low.endswith("_base.chr") or "/nude/" in low:
        stem = p[:-4]
        cands.insert(0, stem[:-5] + "_nude.chr" if low.endswith("_base.chr") else stem + "_nude.chr")
    best = None
    for c in cands:
        raw = idx.read(c)
        if not raw:
            continue
        n = _model_verts(raw)
        if n > 150 and (best is None or n > best[1]):
            best = (idx.get(c), n)
    return best[0] if best else None


def _race_of(body_path: str) -> tuple[str, str] | None:
    m = _HUMAN_BODY.search(body_path or "")
    return (m.group(1).lower(), m.group(2).lower()) if m else None


def _resolve_asset_path(idx: PakIndex, cache: dict, path: str, race: tuple[str, str] | None) -> str | None:
    """item_assets.path -> an existing, parseable model file in the pak.

    Order: exact path -> sibling .cdf/Model-File -> stem fallback (strip
    trailing variant tokens, look up <stem>.cdf/.chr in the pak, preferring
    the NPC's race folder). Cached per path.
    """
    if not path:
        return None
    key = path.replace("\\", "/").lower()
    if key in cache.setdefault("_asset", {}):
        return cache["_asset"][key] or None

    out = None
    p = _game_path(path)
    fname = p.rsplit("/", 1)[1]
    stem_base, _, ext_s = fname.rpartition(".")
    ext = "." + ext_s if stem_base else ""
    if not stem_base:
        stem_base, ext = fname, ""
    # 1) exact hit (chr/cgf) or its .cdf wrapper
    if ext in (".chr", ".cgf"):
        raw = idx.read(p)
        if raw and _model_verts(raw) > _MIN_VERTS:
            out = idx.get(p)
    elif ext == ".cdf":
        out = _cdf_to_chr(idx, cache, p)
    if out is None and ext != ".cdf" and idx.get(p[:-4] + ".cdf"):
        out = _cdf_to_chr(idx, cache, p[:-4] + ".cdf")
    # 2) stem fallback: legacy dirs (…/leather/leather007/x_rope.chr) became
    #    parts/<slot>/<mat>/<slot_matNNN>/<stem>.cdf -> obj/<combined>.chr
    if out is None:
        toks = stem_base.split("_")
        bi = _base_index(idx, cache)
        for n in range(len(toks), 1, -1):
            b = "_".join(toks[:n])
            for c in bi.get(b + ".cdf", []) + bi.get(b + ".chr", []):
                if "/monster/" in c or c.endswith(("_lod1.chr", "_lod2.chr", "_base.chr")):
                    continue
                if race and f"/characters/{race[0]}/{race[1]}/" not in c:
                    continue
                if c.endswith(".cdf"):
                    hit = _cdf_to_chr(idx, cache, c)
                else:
                    raw = idx.read(c)
                    hit = idx.get(c) if raw and _model_verts(raw) > _MIN_VERTS else None
                if hit:
                    out = hit
                    break
            if out:
                break
    cache["_asset"][key] = out or ""
    return out


def _gear_chr(con, idx: PakIndex, cache: dict, item_id: int, look_id: int | None, race) -> str | None:
    """An equip item id -> the .chr/.cgf path to render it (armor chain)."""
    asset_id = _scalar(con, "select asset_id from item_armors where item_id=?", (item_id,))
    if asset_id is None:
        asset_id = _scalar(con, "select asset_id from item_weapons where item_id=?", (item_id,))
    if asset_id is None:
        return None
    path = None
    # armor_assets -> per-race item_assets variants (models.id = item_assets.model_id)
    if _scalar(con, "select count(*) from armor_assets where id=?", (asset_id,)):
        var = None
        if look_id is not None:
            var = _scalar(
                con,
                "select ia.path from item_armor_assets iaa join item_assets ia on ia.id=iaa.asset_id"
                " where iaa.armor_asset_id=? and ia.model_id=? limit 1",
                (asset_id, look_id),
            )
        if var is None:
            default = _scalar(con, "select default_asset_id from armor_assets where id=?", (asset_id,))
            if default:
                var = _scalar(con, "select path from item_assets where id=?", (default,))
        if var is None:
            var = _scalar(
                con,
                "select ia.path from item_armor_assets iaa join item_assets ia on ia.id=iaa.asset_id"
                " where iaa.armor_asset_id=? limit 1",
                (asset_id,),
            )
        path = var
    if path is None:  # legacy/custom rows: asset_id indexes item_assets directly
        path = _scalar(con, "select path from item_assets where id=?", (asset_id,))
    return _resolve_asset_path(idx, cache, path or "", race)


def _bodypart_chr(con, idx: PakIndex, cache: dict, item_id: int, look_id: int | None, race) -> str | None:
    """face/hair/beard item id -> item_body_parts.asset_id -> item_assets.path."""
    if not item_id:
        return None
    path = None
    for q, args in (
        ("select ia.path from item_body_parts bp join item_assets ia on ia.id=bp.asset_id"
         " where bp.item_id=? and (? is null or bp.model_id=? or bp.model_id=0) limit 1", (item_id, look_id, look_id)),
        ("select ia.path from item_body_parts bp join item_assets ia on ia.id=bp.asset_id"
         " where bp.item_id=? limit 1", (item_id,)),
    ):
        path = _scalar(con, q, args)
        if path:
            break
    return _resolve_asset_path(idx, cache, path or "", race)


def _default_chr(idx: PakIndex, cache: dict, race: tuple[str, str], names: list[str]) -> str | None:
    """First existing race-matched default face/hair .chr in the pak (by basename)."""
    bi = _base_index(idx, cache)
    ddc = cache.setdefault("_default", {})
    rd = f"/characters/{race[0]}/{race[1]}/"
    for nm in names:
        for cand in bi.get(nm + ".chr", []):
            if rd not in cand or cand.endswith(("_lod1.chr", "_lod2.chr")):
                continue
            if cand in ddc:
                if ddc[cand]:
                    return ddc[cand]
                continue
            raw = idx.read(cand)
            ok = bool(raw) and _model_verts(raw) > _MIN_VERTS
            ddc[cand] = cand if ok else ""
            if ok:
                return cand
    return None


def resolve_npc_parts(idx: PakIndex, sqlite_path_or_con, npc_id: int, cache: dict) -> list[dict]:
    """Full detail version of resolve_npc_models: [{label, path}, ...]."""
    con = _connect(sqlite_path_or_con, cache)
    cache.setdefault("_asset", {})
    npc = _rows(
        con,
        "select model_id, equip_bodies_id, equip_cloths_id, equip_weapons_id, total_custom_id from npcs where id=?",
        (npc_id,),
    )
    if not npc:
        return []
    model_id, bodies_id, cloths_id, weapons_id, custom_id = npc[0]

    parts: list[dict] = []
    body_file = _scalar(con, "select model_file from actor_models where id=?", (model_id or 0,))
    body = _body_chr(idx, cache, body_file or "")
    if not body:
        return parts
    parts.append({"label": "body", "path": body})

    race = _race_of(body)
    look_id = None
    if race:
        look_id = _scalar(con, "select id from models where lower(name)=?", (f"{race[0]}_{race[1]}",))

    # face + hair: body pack / total custom, else the race's default face01
    face_id = hair_id = beard_id = 0
    if bodies_id:
        r = _rows(con, "select face_id, hair_id, beard_id from equip_pack_body_parts where id=?", (bodies_id,))
        if r:
            face_id, hair_id, beard_id = r[0]
    if custom_id:
        r = _rows(con, "select hair_id from total_character_customs where id=?", (custom_id,))
        if r and r[0][0]:
            hair_id = r[0][0]
    if race:
        prefix = f"{race[0][:2]}_{race[1][0]}"
        f = _bodypart_chr(con, idx, cache, face_id, look_id, race) if face_id else None
        f = f or _default_chr(idx, cache, race, [f"{prefix}_face01", f"{prefix}_face00"])
        if f:
            parts.append({"label": "face", "path": f})
        h = _bodypart_chr(con, idx, cache, hair_id, look_id, race) if hair_id else None
        if h:
            parts.append({"label": "hair", "path": h})
        b = _bodypart_chr(con, idx, cache, beard_id, look_id, race) if beard_id else None
        if b:
            parts.append({"label": "beard", "path": b})

    # clothing
    if cloths_id:
        cols = [c for c, _ in CLOTH_SLOTS]
        row = _rows(con, f"select {', '.join(cols)} from equip_pack_cloths where id=?", (cloths_id,))
        if row:
            for (col, label), iid in zip(CLOTH_SLOTS, row[0]):
                if not iid:
                    continue
                p = _gear_chr(con, idx, cache, iid, look_id, race)
                if p:
                    parts.append({"label": label, "path": p, "item_id": iid})
                elif cache.get("verbose"):
                    print("  npc", npc_id, "unresolved", label, "item", iid)

    # weapons
    if weapons_id:
        row = _rows(con, "select mainhand_id, offhand_id, ranged_id from equip_pack_weapons where id=?", (weapons_id,))
        if row:
            for (col, label), iid in zip(WEAPON_SLOTS, row[0]):
                if not iid:
                    continue
                asset_id = _scalar(con, "select asset_id from item_weapons where item_id=?", (iid,))
                path = _scalar(con, "select path from item_assets where id=?", (asset_id or 0,))
                p = _resolve_asset_path(idx, cache, path or "", None)
                if p:
                    parts.append({"label": label, "path": p, "item_id": iid})

    # de-dup, keep order (body mesh may itself be listed twice via cdf chain)
    seen = set()
    out = []
    for pt in parts:
        k = pt["path"].lower()
        if k not in seen:
            seen.add(k)
            out.append(pt)
    return out


def resolve_npc_models(idx: PakIndex, sqlite_path_or_con, npc_id: int, cache: dict) -> list[str]:
    """npc id -> ordered list of EXISTING, parsable .chr/.cgf pak paths:
    body, face, [hair, beard], chest, legs, ..., headgear, weapons."""
    return [p["path"] for p in resolve_npc_parts(idx, sqlite_path_or_con, npc_id, cache)]


def load_npc_meshes(idx: PakIndex, sqlite_path_or_con, npc_id: int, cache: dict) -> tuple[list[dict], list[dict]]:
    """Parsed meshes + part records for an npc id (each verified > 50 verts)."""
    parts = resolve_npc_parts(idx, sqlite_path_or_con, npc_id, cache)
    meshes = []
    kept = []
    mcache = cache.setdefault("_mesh", {})
    for pt in parts:
        key = pt["path"].lower()
        if key not in mcache:
            mcache[key] = _parse_any(idx.read(pt["path"]) or b"")
        mesh = mcache[key]
        if mesh and len(mesh["positions"]) // 3 > _MIN_VERTS:
            meshes.append(mesh)
            kept.append(pt)
    return meshes, kept


def compose_chr(meshes: list[dict], sources: list[str] | None = None) -> dict | None:
    """Concatenate parsed .chr dicts (parse_chr output shape) into ONE mesh.

    All characters share the same skeleton/bind pose, so vertex/index offset
    in bind pose is correct for a static view. Per-part subsets keep their
    material name ('mat') and source model ('part') so the baker can resolve
    each part's .mtl/textures from its own folder. The merged 'materials'
    list is prefixed with "" so names[1:] indexes subset.matId directly.
    """
    if not meshes:
        return None
    pos: list[float] = []
    nrm: list[float] = []
    uv: list[float] = []
    indices: list[int] = []
    subsets: list[dict] = []
    materials: list[str] = [""]
    for i, m in enumerate(meshes):
        src = (sources or [None] * len(meshes))[i]
        n0 = len(pos) // 3
        i0 = len(indices)
        m0 = len(materials) - 1
        pos.extend(m.get("positions") or [])
        nrm.extend(m.get("normals") or [0.0] * len(m.get("positions") or []))
        uv.extend(m.get("uvs") or [0.0] * len(m.get("positions") or []))
        nv = len(m.get("positions") or []) // 3
        indices.extend(int(x) + n0 for x in m.get("indices") or [] if 0 <= int(x) < nv)
        names = m.get("materials") or []
        children = names[1:] if len(names) > 1 else names
        materials.extend(children)
        for s in m.get("subsets") or []:
            fi = min(int(s.get("firstIndex") or 0), len(m.get("indices") or []))
            ni = min(int(s.get("indexCount") or 0), len(m.get("indices") or []) - fi)
            if ni <= 0:
                continue
            subsets.append(
                {
                    "firstIndex": i0 + fi,
                    "indexCount": ni,
                    "mat": s.get("mat") or "",
                    "matId": m0 + int(s.get("matId") or 0),
                    "part": src or "",
                }
            )
    if not indices or not subsets:
        return None
    n = len(pos) // 3
    if len(nrm) != n * 3:
        nrm = nrm[: n * 3] + [0.0] * (n * 3 - len(nrm))
    if len(uv) != n * 2:
        uv = uv[: n * 2] + [0.0] * (n * 2 - len(uv))
    return {
        "positions": pos,
        "normals": nrm,
        "uvs": uv,
        "indices": indices,
        "subsets": subsets,
        "materials": materials,
    }


def _self_test() -> int:
    import json
    import tempfile

    root = Path(__file__).resolve().parent.parent.parent
    pak = root / ".client_files/ArcheAge 1.2 (r208022) for AAEmu/game_pak"
    db = root / ".client_files/ArcheAge 1.2 (r208022) for AAEmu/compact.sqlite3"
    out = Path(tempfile.gettempdir()) / "archeaage-npcmodel"
    out.mkdir(parents=True, exist_ok=True)
    idx = PakIndex(open_pak(pak))
    cache: dict = {"verbose": True}
    rc = 0
    for nid in (502, 727, 6077, 3969):
        parts = resolve_npc_parts(idx, db, nid, cache)
        name = _scalar(_connect(db, cache), "select name from npcs where id=?", (nid,))
        print(f"\n=== npc {nid} ({name}) : {len(parts)} parts ===")
        for p in parts:
            print(f"  {p['label']:>10}  {p['path']}")
        meshes, kept = load_npc_meshes(idx, db, nid, cache)
        body_v = len(meshes[0]["positions"]) // 3 if meshes else 0
        comp = compose_chr(meshes, [p["path"] for p in kept])
        assert comp, f"npc {nid}: compose failed"
        n = len(comp["positions"]) // 3
        assert len(comp["normals"]) == n * 3 and len(comp["uvs"]) == n * 2, "uv/normals mismatch"
        assert comp["indices"] and max(comp["indices"]) < n, "index out of range"
        for s in comp["subsets"]:
            assert 0 <= s["firstIndex"] and s["firstIndex"] + s["indexCount"] <= len(comp["indices"])
            assert 0 <= s["matId"] < len(comp["materials"]) - 1 or not comp["materials"][1:]
        tv = sum(len(m["positions"]) // 3 for m in meshes)
        assert n == tv, "vertex rebasing lost/duplicated verts"
        extra = n - body_v
        if len(meshes) > 1:
            if extra <= 0:
                print(f"  FAIL npc {nid}: composed {n} <= body {body_v}")
                rc = 1
        else:
            print(f"  (monster npc: body only, {n} verts)")
        print(f"  verts: body={body_v} composed={n} (+{extra})  subsets={len(comp['subsets'])} mats={len(comp['materials']) - 1}")
        dest = out / f"npcmodel_selftest_{nid}.json"
        dest.write_text(json.dumps({"npc": nid, "name": name, "parts": parts, "mesh": comp}), encoding="utf-8")
        print("  wrote", dest)
    print("\nself-test", "OK" if rc == 0 else "FAILED")
    return rc


if __name__ == "__main__":
    import sys

    if "--self-test" in sys.argv:
        raise SystemExit(_self_test())
    print(__doc__)
