#!/usr/bin/env python3
"""entities.py — parse ArcheAge cell entities.xml (CryEngine Sandbox format).

Each <Entity> becomes:
  {name, class, pos:[x,y,z], rotate:[w,x,y,z], scale:[x,y,z],
   model, layer, material}
Missing attributes default: pos=[0,0,0], rotate=[1,0,0,0], scale=[1,1,1].

Parsed with a regex over <Entity ...> opening tags (no XML parser):
the file is a flat list of Entity elements whose attributes carry all
the data we need. Stdlib-only, no external XML security concerns.
"""

import re
from pathlib import Path

_ENTITY_TAG = re.compile(r"<Entity\b([^>]*)>")
_ATTR = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"([^"]*)"')
# object_Model lives in the <Properties> child of an Entity
_MODEL = re.compile(r'object_Model="([^"]*)"')


def _vec3(value: str | None, default):
    if not value:
        return list(default)
    try:
        parts = [float(x) for x in value.split(",")]
        return parts[:3] if len(parts) >= 3 else list(default)
    except ValueError:
        return list(default)


def _vec4(value: str | None, default):
    if not value:
        return list(default)
    try:
        parts = [float(x) for x in value.split(",")]
        return parts[:4] if len(parts) >= 4 else list(default)
    except ValueError:
        return list(default)


def _attrs(tag_body: str) -> dict:
    return {m.group(1): m.group(2) for m in _ATTR.finditer(tag_body)}


def parse_entities_text(text: str) -> list[dict]:
    """Parse entities.xml from a string."""
    entities = []
    for m in _ENTITY_TAG.finditer(text):
        props = _attrs(m.group(1))
        # model is on the <Properties ... object_Model="..."> child element
        body = text[m.end() : m.end() + 2048]
        model_m = _MODEL.search(body)
        entities.append(
            {
                "name": props.get("Name", ""),
                "class": props.get("EntityClass", ""),
                "pos": _vec3(props.get("Pos"), (0.0, 0.0, 0.0)),
                "rotate": _vec4(props.get("Rotate"), (1.0, 0.0, 0.0, 0.0)),
                "scale": _vec3(props.get("Scale"), (1.0, 1.0, 1.0)),
                "model": (model_m.group(1) if model_m else "")
                or props.get("object_Model", "")
                or props.get("Model", ""),
                "layer": props.get("Layer", ""),
                "material": props.get("Material", ""),
            }
        )
    return entities


def parse_entities(path: Path) -> list[dict]:
    """Parse entities.xml into a list of entity dicts."""
    return parse_entities_text(path.read_text(encoding="utf-8", errors="replace"))


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    ents = parse_entities(Path(sys.argv[1]))
    print(json.dumps(ents, indent=1, ensure_ascii=False))
    print(f"# {len(ents)} entities")
