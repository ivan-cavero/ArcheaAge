"""Parse CryEngine .mtl XML for diffuse maps and alpha-test."""

from __future__ import annotations

import re
from pathlib import Path

_TEX = re.compile(r"<Texture\b([^>]*)>", re.I)
_TEXMAP = re.compile(r'\bMap="([^"]*)"', re.I)
_TEXFILE = re.compile(r'\bFile="([^"]*)"', re.I)
_NAME = re.compile(r'\bName="([^"]*)"')
_ATEST = re.compile(r'\bAlphaTest="([^"]*)"')
_SHADER = re.compile(r'\bShader="([^"]*)"')
_MAT_START = re.compile(r"<Material\b", re.I)


def _norm(p: str) -> str:
    p = p.replace("\\", "/").lstrip("/")
    if p.lower().startswith("game/"):
        return p
    if p.lower().startswith(("objects/", "textures/", "materials/")):
        return "game/" + p
    return p


def _attrs(tag_text: str) -> dict[str, str]:
    return dict(re.findall(r'(\w+)="([^"]*)"', tag_text))


def parse_mtl(text: str) -> dict[str, dict]:
    """name -> {diffuse, alphaTest, shader, opacity}.

    CryEngine .mtl files nest the real materials as <SubMaterials><Material
    Name="..."/></SubMaterials> inside a parent <Material> whose opening tag
    has NO Name. We register every submaterial by name, and the parent by its
    file stem (the CGF MtlName list references both).
    """
    out: dict[str, dict] = {}

    def build(attrs: dict, name: str) -> dict | None:
        shader = attrs.get("Shader", "")
        if shader.lower() == "nodraw":
            return None
        try:
            alpha = float(attrs.get("AlphaTest") or 0)
        except ValueError:
            alpha = 0.0
        if alpha == 0.0 and ("leaf" in name.lower() or "opac" in name.lower()):
            alpha = 0.5
        return {
            "alphaTest": alpha,
            "shader": shader,
            "opacity": "",
            "diffuse": "",
        }

    # split into top-level material chunks at <Material ...> openings that are
    # NOT nested submaterials: a parent tag is followed (eventually) by
    # <SubMaterials>. Simpler: iterate every <Material tag, sub tags win by
    # name; parents register under the file stem later.
    starts = list(_MAT_START.finditer(text))
    for i, m in enumerate(starts):
        seg_end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        chunk = text[m.start() : seg_end]
        gt = chunk.find(">")
        if gt < 0:
            continue
        attrs = _attrs(chunk[:gt])
        name = attrs.get("Name") or ""
        info = build(attrs, name) if name else None
        if info is None:
            continue
        maps = {}
        for tm in _TEX.finditer(chunk):
            a = tm.group(1)
            mk = _TEXMAP.search(a)
            fv = _TEXFILE.search(a)
            if mk and fv:
                maps[mk.group(1).lower()] = _norm(fv.group(1))
        info["diffuse"] = maps.get("diffuse") or maps.get("opacity") or ""
        info["opacity"] = maps.get("opacity", "")
        out[name] = info
    return out


def parse_mtl_file(path: Path) -> dict[str, dict]:
    return parse_mtl(path.read_text(encoding="utf-8", errors="replace"))


def mtl_candidates(model_path: str) -> list[str]:
    p = model_path.replace("\\", "/")
    stem = p.rsplit(".", 1)[0]
    parent = stem.rsplit("/", 1)[0]
    base = stem.rsplit("/", 1)[-1]
    stripped = re.sub(r"(_?\d+[a-z]?)+$", "", base, flags=re.I)
    out = [
        stem + ".mtl",
        parent + "/" + stripped + ".mtl",
        parent + "/" + re.sub(r"_+\d.*$", "", base) + ".mtl",
    ]
    seen: list[str] = []
    for x in out:
        if x and x not in seen:
            seen.append(x)
    return seen


def best_folder_mtl(model_path: str, folder_mtls: list[str]) -> str | None:
    base = model_path.replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
    best = None
    score = 4
    for m in folder_mtls:
        mb = m.replace("\\", "/").rsplit("/", 1)[-1].replace(".mtl", "").lower()
        n = 0
        for a, b in zip(base, mb):
            if a == b:
                n += 1
            else:
                break
        if n > score:
            score = n
            best = m
    return best
