#!/usr/bin/env python3
"""tex.py — extract / brand / replace background textures in the client pak.

Requires: Pillow (pip install pillow). Read path is Python (`tools.pak`);
write/replace still uses tools/pak-put (C#).

Usage:
  python tex.py extract <game_pak> <pak_entry> <out.png>
  python tex.py brand   <game_pak> <pak_entry> <text>     # stamp text bottom-right
  python tex.py replace <game_pak> <pak_entry> <in.png>   # resize+convert+inject
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.pak import open_pak  # noqa: E402

PAK_PUT = ROOT / "tools" / "pak-put"
TMP = ROOT / ".client_files" / ".tex_tmp"


def extract_dds(pak, entry, out_dds):
    with open_pak(pak) as gp:
        data = gp.read(entry)
        if data is None:
            matches = gp.list_entries(entry)
            if not matches:
                raise SystemExit(f"entry not found in pak: {entry}")
            data = gp.read(matches[0][0])
    Path(out_dds).parent.mkdir(parents=True, exist_ok=True)
    Path(out_dds).write_bytes(data)


def dds_to_png(dds_path, png_path):
    img = Image.open(dds_path)
    img.convert("RGB").save(png_path)
    return img.size


def png_to_dds(png_path, dds_path, size=None):
    img = Image.open(png_path).convert("RGB")
    if size and img.size != size:
        img = img.resize(size, Image.LANCZOS)
    # DXT5 keeps quality reasonable; Pillow writes BC3 when mode has alpha
    rgba = img.convert("RGBA")
    rgba.save(dds_path, format="DDS", compression="dxt5")


def main():
    cmd = sys.argv[1]
    pak = sys.argv[2]
    entry = sys.argv[3]

    TMP.mkdir(parents=True, exist_ok=True)

    if cmd == "extract":
        out_png = sys.argv[4]
        tmp_dds = TMP / "extract.dds"
        extract_dds(pak, entry, tmp_dds)
        size = dds_to_png(tmp_dds, out_png)
        print(f"extracted {entry} -> {out_png} ({size[0]}x{size[1]})")

    elif cmd == "brand":
        text = sys.argv[4] if len(sys.argv) > 4 else "ArcheaAge"
        tmp_dds = TMP / "brand_orig.dds"
        extract_dds(pak, entry, tmp_dds)
        img = Image.open(tmp_dds).convert("RGB")
        draw = ImageDraw.Draw(img, "RGBA")
        font = None
        for candidate in ("segoeuib.ttf", "arialbd.ttf", "arial.ttf"):
            try:
                import PIL.ImageFont as F
                font = F.truetype(candidate, max(18, img.height // 22))
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = img.width - tw - int(img.width * 0.03), img.height - th - int(img.height * 0.04)
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 200),
                  stroke_width=2, stroke_fill=(0, 0, 0, 180))
        branded = TMP / "brand_new.png"
        img.save(branded)
        new_dds = TMP / "brand_new.dds"
        png_to_dds(branded, new_dds, img.size)
        out = subprocess.run(["dotnet", "run", "--project", str(PAK_PUT), "--",
                              pak, str(new_dds), entry], capture_output=True, text=True)
        tail = "\n".join((out.stdout + out.stderr).splitlines()[-3:])
        print(tail)
        if out.returncode != 0 or "VERIFIED ok" not in (out.stdout + out.stderr):
            raise SystemExit("pak-put failed")

    elif cmd == "replace":
        in_png = Path(sys.argv[4])
        tmp_dds = TMP / "orig_for_size.dds"
        extract_dds(pak, entry, tmp_dds)
        orig_size = Image.open(tmp_dds).size
        new_dds = TMP / "replaced.dds"
        png_to_dds(in_png, new_dds, orig_size)
        out = subprocess.run(["dotnet", "run", "--project", str(PAK_PUT), "--",
                              pak, str(new_dds), entry], capture_output=True, text=True)
        tail = "\n".join((out.stdout + out.stderr).splitlines()[-3:])
        print(tail)
        if out.returncode != 0 or "VERIFIED ok" not in (out.stdout + out.stderr):
            raise SystemExit("pak-put failed")

    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
