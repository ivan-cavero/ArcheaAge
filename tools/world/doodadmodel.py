#!/usr/bin/env python3
"""doodadmodel.py — resolve AAEmu doodad spawn UnitIds to pak model files.

Discovered chain (verified against AAEmu.Game sources + compact.sqlite3):

    doodad_spawns.json entry.UnitId  ==  doodad_almighties.id   (template id,
                                                                  NOT a runtime id)
    doodad_almighties.model          ==  model URI, one of:
        cgf://<path>            plain geometry file  (game/objects/env/...)
        cga://<path>            animated .cga OR a .chr path (ships, animals)
        vegetation://<path>     tree .cgf (CryData VegetationPath)
        prefab://<lib>.xml/<EntryName>
                                CryEngine prefabs library entry; the real mesh
                                is referenced inside the XML by
                                <Object Prefab="..."/> (Brush) or
                                object_Model="..." (AnimObject Entity)
        <bare path>             rare: a direct .cgf path without a scheme
        ''                      empty → fall back to the doodad's first
                                non-empty doodad_func_groups.model (phase
                                model; same URI grammar)

Why this chain: DoodadManager.LoadGameTables reads `doodad_almighties` keyed
by id (Core/Managers/UnitManagers/DoodadManager.cs, "SELECT * from
doodad_almighties"), DoodadSpawner.TemplateId/UnitId reference that id, and
JsonDoodadSpawns.UnitId (Models/Json/JsonDoodadSpawns.cs) is what
worlds/main_world/doodad_spawns.json stores. compact.sqlite3 carries the
client-side copy including the `model` column the server never reads (the
client resolves it itself).

Path normalization: DB paths mix "\" and "/", inconsistently case the "game/"
prefix (or omit it), carry stray whitespace and trailing "/". They are
cleaned (collapse //, strip spaces in the file name, drop trailing ./, force
"game/" prefix) and matched case-insensitively against the pak index; a
unique-basename fallback recovers dev-moved assets. Prefab XMLs are read from
the pak (game/prefabs/*.xml) and cached per library.

main_world self-test: 2241/2298 unique spawn UnitIds (97.5%) resolve to an
existing pak file and 42,414/42,649 spawn *instances* (99.4%) get a model;
of the 1910 unique model files 1885 parse, the other 25 being
proxy/invisible/box ship-part helpers that legitimately have no renderable
geometry. Remaining misses are placeholders (invisible/sound/particle
prefabs), assets trimmed from the 1.2 client (e.g. cat_baby_pet), or
dev-stale DB paths.

Usage:

    from tools.world.doodadmodel import load_doodad_models, is_chr
    models = load_doodad_models(db_path, idx)   # {unit_id: "game/....cgf"}
    parser = parse_chr if is_chr(models[u]) else parse_cgf

`idx` is any object with .get(name)/.read(name) (tools.pak.PakIndex).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

_MODEL_ATTR = re.compile(r'(?:\bPrefab|\bobject_Model)="([^"]+?\.(?:cgf|chr|cga))\s*"', re.I)
_URI = re.compile(r"(\w+)://(.*)$", re.S)
_PREFAB_PARTS = re.compile(r"(.*?\.xml)/(.+)$", re.S | re.I)
_PREFAB_OPEN = re.compile(r'<Prefab\s+Name="([^"]+)"', re.I)
_CDF_MODEL = re.compile(r'<Model\s+File="([^"]+)"', re.I)
_MESH_EXT = (".cgf", ".chr", ".cga")


def is_chr(path: str) -> bool:
    """True if the resolved model path is a skeletal .chr (else .cgf/.cga)."""
    return path.lower().endswith(".chr")


def norm_pak_path(p: str) -> str:
    """Clean a DB/prefab model path into a canonical pak-relative path."""
    p = p.replace("\\", "/").strip().rstrip("/").strip()
    if not p:
        return ""
    folder, _, name = p.rpartition("/")
    name = re.sub(r"\s+", "", name)  # "bro_apart_door_default .cgf"
    p = (folder + "/" + name) if folder else name
    p = re.sub(r"/{2,}", "/", p)
    if not p.lower().startswith("game/"):
        p = "game/" + p
    return p


def _prefab_library(idx, xml_path: str, cache: dict) -> dict[str, list[str]]:
    """Parse a prefabs library XML: {entry_name_lower: [model paths]}."""
    key = xml_path.lower()
    if key in cache:
        return cache[key]
    entries: dict[str, list[str]] = {}
    raw = idx.read(xml_path)
    if raw:
        txt = raw.decode("utf-8", "replace")
        for m in _PREFAB_OPEN.finditer(txt):
            start = m.end()
            end = txt.find("</Prefab>", start)
            nxt = txt.find("<Prefab ", start)  # self-closed / unclosed entry
            if end < 0 or 0 <= nxt < end:
                end = nxt
            body = txt[start : end if end >= 0 else start + 8000]
            models = _MODEL_ATTR.findall(body)
            if models:
                entries.setdefault(m.group(1).strip().lower(), []).extend(models)
    cache[key] = entries
    return entries


def _build_name_index(idx) -> dict[str, list[str]]:
    """basename -> canonical pak entries (for the unique-basename fallback)."""
    table: dict[str, list[str]] = {}
    lower = getattr(idx, "lower", None)
    if not lower:
        return table
    for low, orig in lower.items():
        if low.endswith(_MESH_EXT):
            table.setdefault(low.rsplit("/", 1)[-1], []).append(orig)
    return table


def _lookup(idx, path: str, name_idx: dict[str, list[str]]) -> str | None:
    """Canonical pak entry for a cleaned path (exact, else unique basename)."""
    hit = idx.get(path)
    if hit:
        return hit
    cands = name_idx.get(path.lower().rsplit("/", 1)[-1] or "")
    if cands and len(cands) == 1:
        return cands[0]
    return None


def _chr_for_cdf(idx, path: str, name_idx: dict) -> str | None:
    """A .cdf is an XML character def; its <Model File=""/> names the .chr body."""
    raw = idx.read(path)
    if not raw:
        return None
    m = _CDF_MODEL.search(raw.decode("utf-8", "replace"))
    if not m:
        return None
    chr_path = _lookup(idx, norm_pak_path(m.group(1)), name_idx)
    if chr_path and chr_path.lower().endswith(".chr"):
        return chr_path
    return None


def _resolve_uri(idx, uri: str, xml_cache: dict, name_idx: dict) -> str | None:
    """Map one doodad model URI (or bare path) to a pak entry name."""
    uri = (uri or "").strip()
    if not uri:
        return None
    m = _URI.match(uri)
    if not m:  # bare path
        return _lookup(idx, norm_pak_path(uri), name_idx)
    scheme, rest = m.group(1).lower(), m.group(2).strip()
    if scheme == "prefab":
        pm = _PREFAB_PARTS.match(rest)
        if not pm:
            return None
        lib = _prefab_library(idx, norm_pak_path(pm.group(1)), xml_cache)
        for sub in lib.get(pm.group(2).strip().lower(), []):
            hit = _lookup(idx, norm_pak_path(sub), name_idx)
            if hit:
                return hit
        return None
    if scheme in ("cgf", "cga", "chr", "vegetation", "cdf"):
        return _lookup(idx, norm_pak_path(rest), name_idx)
    return None  # unknown scheme (decal/effect-only etc.)


def load_doodad_models(db_path: Path | str, idx) -> dict[int, str]:
    """{spawn UnitId -> pak model path} for every doodad template the DB knows.

    Keys are doodad_almighties.id (== doodad_spawns.json UnitId); values are
    pak entry names ending in .cgf/.cga/.chr (see is_chr). Templates that only
    exist as particles/sounds/proxies or whose asset is missing from the pak
    are simply absent from the dict. Paths are case-insensitively matched
    against `idx`; requires idx.get()/idx.read() (tools.pak.PakIndex).
    """
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        rows = cur.execute("SELECT id, model FROM doodad_almighties").fetchall()
        # Phase-model fallback for templates with an empty almighty model:
        # the first non-empty doodad_func_groups row (lowest id) for that almighty.
        phase_model: dict[int, str] = {}
        try:
            for am, model in cur.execute(
                "SELECT doodad_almighty_id, model FROM doodad_func_groups "
                "WHERE model IS NOT NULL AND model != '' ORDER BY id"
            ):
                phase_model.setdefault(int(am), model)
        except sqlite3.Error:
            pass
    finally:
        con.close()

    xml_cache: dict[str, dict[str, list[str]]] = {}
    name_idx = _build_name_index(idx)
    models: dict[int, str] = {}
    for tid, uri in rows:
        path = _resolve_uri(idx, uri or "", xml_cache, name_idx)
        if not path:
            path = _resolve_uri(idx, phase_model.get(int(tid), ""), xml_cache, name_idx)
        if path and path.lower().endswith(".cdf"):
            path = _chr_for_cdf(idx, path, name_idx)  # character def -> body mesh
        if path:
            models[int(tid)] = path.replace("\\", "/")
    return models


if __name__ == "__main__":
    import json
    import sys
    from collections import Counter
    from pathlib import Path as _P

    _root = _P(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(_root))
    from tools.pak import PakIndex, open_pak
    from tools.world.cgf import parse_cgf
    from tools.world.chr import parse_chr

    def load_jsonc(p):
        t = p.read_text(encoding="utf-8")
        t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
        t = re.sub(r"//[^\n]*", "", t)
        return json.loads(re.sub(r",\s*([}\]])", r"\1", t))

    world = sys.argv[1] if len(sys.argv) > 1 else "main_world"
    db = _root / ".client_files/ArcheAge 1.2 (r208022) for AAEmu/compact.sqlite3"
    pak = _root / ".client_files/ArcheAge 1.2 (r208022) for AAEmu/game_pak"
    spawns = _root / f"servers/aaemu/AAEmu.Game/Data/Worlds/{world}/doodad_spawns.json"

    idx = PakIndex(open_pak(pak))
    models = load_doodad_models(db, idx)
    print(f"templates with a resolvable model: {len(models)}")

    weight = Counter(int(e["UnitId"]) for e in load_jsonc(spawns))
    units = set(weight)
    found = units & set(models)
    inst = sum(weight[u] for u in found)
    print(f"{world}: {len(units)} unique spawn UnitIds, {len(found)} resolve "
          f"({100 * len(found) / len(units):.1f}%)")
    print(f"spawn instances {inst}/{sum(weight.values())} = {100 * inst / sum(weight.values()):.1f}%")

    print("\n== chain proof (UnitId -> template -> model -> pak file -> verts) ==")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    for u in sorted(found)[:8]:
        uri, name = con.execute(
            "SELECT model, name FROM doodad_almighties WHERE id=?", (u,)
        ).fetchone()
        path = models[u]
        raw = idx.read(path)
        mesh = (parse_chr if is_chr(path) else parse_cgf)(raw)
        verts = len(mesh["positions"]) // 3 if mesh else 0
        print(f"  {u:5d} {name[:18]!r:22} {(uri or '')[:58]!r:60} -> {path[-52:]} ({len(raw)}B, {verts} verts, {'OK' if verts else 'EMPTY'})")
    con.close()

    ext = Counter(p.rsplit(".", 1)[-1].lower() for p in models.values())
    print("\nresolved extensions:", dict(ext))
    unparsable = []
    for p in sorted(set(models.values())):
        raw = idx.read(p)
        mesh = (parse_chr if is_chr(p) else parse_cgf)(raw)
        if not mesh or len(mesh["positions"]) < 3:
            unparsable.append(p)
    print(f"unique model files: {len(set(models.values()))}, unparsable/proxy: {len(unparsable)}")
    for p in unparsable:
        print("   ", p)
