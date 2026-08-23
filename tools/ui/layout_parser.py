#!/usr/bin/env python3
"""layout_parser.py — extracts widget layout (positions/sizes) from decompiled
ArcheAge UI Lua sources and computes absolute screen rectangles.

Reads the AddAnchor/SetExtent/CreateChildWidget calls from decompiled sources,
resolves the anchor chain, and outputs absolute x/y/w/h per widget assuming a
1920x1080 UIParent.

Usage:
  python layout_parser.py <decompiled.lua> [more.lua ...] -o layout.json

Output JSON:
{
  "screen": "...",
  "viewport": [1920, 1080],
  "widgets": [
    {"id":"mainWindow","parent":"backgroundWindow","x":620,"y":480,"w":798,"h":22}
  ]
}

Anchors are resolved to a single representative point (the widget's top-left
when possible, otherwise its center). Complex stretch anchors produce the
union rect. This is an approximation good enough to *see* where things are.
"""
import json
import re
import sys


def parse_sources(paths):
    """Extract widget declarations, extents and anchors from decompiled Lua."""
    widgets = {}    # varname -> {parent_var, type, wid, anchor, extent}
    order = []

    # varName = parentVar:CreateChildWidget("type", "id", layer, ...)
    re_create = re.compile(
        r'(\w+)\s*=\s*(\w+):Create(?:Child)?(?:Widget|Window)\('
        r'"[^"]*"\s*,\s*"([^"]*)"')
    # varName = CreateEmptyWindow("id", "parent")
    re_win = re.compile(r'(\w+)\s*=\s*CreateEmptyWindow\("([^"]*)"\s*,\s*"([^"]*)"\)')
    # varName:SetExtent(w, h)
    re_extent = re.compile(r'(\w+)\s*:SetExtent\(\s*(\d+)\s*,\s*(\d+)\s*\)')
    # varName:SetWidth(n) / SetHeight(n)
    re_w = re.compile(r'(\w+)\s*:SetWidth\(\s*(\d+)\s*\)')
    re_h = re.compile(r'(\w+)\s*:SetHeight\(\s*(\d+)\s*\)')
    # varName:AddAnchor("POINT", targetVar, relPoint?, x, y)
    re_anchor = re.compile(
        r'(\w+)\s*:AddAnchor\(\s*"(\w+)"\s*,\s*(?:"(\w+)"|([\w.]+))'
        r'(?:\s*,\s*"(\w+)")?\s*(?:,\s*(-?\d+)\s*,\s*(-?\d+))?')

    body = "\n".join(open(p, encoding="utf-8", errors="replace").read() for p in paths)

    for m in re_create.finditer(body):
        var, parent, _wid = m.groups()
        if var not in widgets:
            widgets[var] = {"id": _wid or var, "parent_var": parent, "anchor": None,
                            "extent": None, "order": len(order)}
            order.append(var)

    for m in re_win.finditer(body):
        var, _wid, parent = m.groups()
        if var not in widgets:
            widgets[var] = {"id": _wid or var, "parent_var": parent, "anchor": None,
                            "extent": None, "order": len(order)}
            order.append(var)

    for m in re_extent.finditer(body):
        var, w, h = m.groups()
        if var in widgets:
            widgets[var]["extent"] = (int(w), int(h))

    for m in re_w.finditer(body):
        var, w = m.groups()
        if var in widgets:
            e = widgets[var].get("extent")
            widgets[var]["extent"] = (int(w), e[1] if e else 0)

    for m in re_h.finditer(body):
        var, h = m.groups()
        if var in widgets:
            e = widgets[var].get("extent")
            widgets[var]["extent"] = ((e[0] if e else 0), int(h))

    for m in re_anchor.finditer(body):
        var, point, target_str, target_expr, relpoint, ox, oy = m.groups()
        if var in widgets:
            widgets[var]["anchor"] = {
                "point": point,
                "target": target_str or target_expr or "",
                "rel_point": relpoint,
                "ox": int(ox or 0),
                "oy": int(oy or 0),
            }

    return widgets, order


def resolve(widgets, order, viewport=(1920, 1080), max_depth=12):
    """Compute absolute rects. Returns {var: {x,y,w,h}}."""
    VPW, VPH = viewport
    rects = {}

    def rect_of(var, depth):
        if var in rects:
            return rects[var]
        if var == "UIParent" or var not in widgets:
            return (0, 0, VPW, VPH)
        if depth > max_depth:
            return (0, 0, 200, 40)

        w = widgets[var]
        px, py, pw, ph = rect_of(w["parent_var"], depth + 1)

        ext = w.get("extent")
        ew, eh = (ext[0], ext[1]) if ext else (200, 30)

        a = w.get("anchor") or {"point": "TOPLEFT", "target": w["parent_var"],
                                 "ox": 0, "oy": 0}
        pt, tgt, ox, oy = a["point"], a["target"], a["ox"], a["oy"]
        tx, ty, tw, th = rect_of(tgt if tgt != "UIParent" else "__screen__", depth + 1) \
            if tgt != "UIParent" else (0, 0, VPW, VPH)

        # start: target's top-left
        x, y = tx, ty

        if pt == "CENTER":
            x = tx + tw // 2 + ox - ew // 2
            y = ty + th // 2 + oy - eh // 2
        elif pt == "TOP":
            x = tx + tw // 2 + ox - ew // 2
            y = ty + oy
        elif pt == "BOTTOM":
            x = tx + tw // 2 + ox - ew // 2
            y = ty + th + oy - eh
        elif pt == "LEFT":
            x = tx + ox - ew
            y = ty + th // 2 + oy - eh // 2
        elif pt == "RIGHT":
            x = tx + tw + ox
            y = ty + th // 2 + oy - eh // 2
        elif pt == "TOPLEFT":
            x = tx + ox; y = ty + oy
        elif pt == "TOPRIGHT":
            x = tx + tw + ox - ew; y = ty + oy
        elif pt == "BOTTOMLEFT":
            x = tx + ox; y = ty + th + oy - eh
        elif pt == "BOTTOMRIGHT":
            x = tx + tw + ox - ew; y = ty + th + oy - eh
        else:  # fallback TOPLEFT
            x = tx + ox; y = ty + oy

        rects[var] = (max(0, x), max(0, y), ew, eh)
        return rects[var]

    for v in order:
        rect_of(v, 0)
    return rects


def main():
    args = sys.argv[1:]
    out_idx = args.index("-o") if "-o" in args else len(args)
    sources = [a for i, a in enumerate(args[:out_idx]) if i != out_idx]
    out_path = args[out_idx + 1] if out_idx < len(args) else "layout.json"

    widgets, order = parse_sources(sources)
    rects = resolve(widgets, order)

    result = {"viewport": [1920, 1080], "widgets": []}
    for var in order:
        r = rects.get(var, {})
        w = widgets[var]
        result["widgets"].append({
            "var": var,
            "id": w.get("id", var),
            "type": w.get("type", ""),
            "x": r[0] if isinstance(r, tuple) else 0,
            "y": r[1] if isinstance(r, tuple) else 0,
            "w": r[2] if isinstance(r, tuple) else 0,
            "h": r[3] if isinstance(r, tuple) else 0,
            "text": "",
        })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"layout.json: {len(result['widgets'])} widgets")


if __name__ == "__main__":
    main()
