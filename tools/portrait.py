# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow"]
# ///
"""Crop a source image to 4:5 and write a portrait and a thumbnail as WebP.

Usage: uv run tools/portrait.py <source-image> <slug>
"""

import io
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent / "images" / "portraits"
RATIO = 4 / 5
ANCHOR_Y = 0.2  # like CSS object-position: center 20%
QUALITY = 75


def crop_4x5(img: Image.Image) -> Image.Image:
    w, h = img.size
    if w / h > RATIO:
        new_w, new_h = round(h * RATIO), h
    else:
        new_w, new_h = w, round(w / RATIO)
    left = round((w - new_w) / 2)
    top = round((h - new_h) * ANCHOR_Y)
    return img.crop((left, top, left + new_w, top + new_h))


def save(img: Image.Image, path: Path, size: tuple[int, int]) -> None:
    # Never upscale beyond the source.
    target = (min(size[0], img.width), min(size[1], img.height))
    out = img.resize(target, Image.LANCZOS) if target != img.size else img
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path, "WEBP", quality=QUALITY, method=6)
    print(f"{path.relative_to(ROOT.parent.parent)}: {out.width}x{out.height}, {path.stat().st_size} bytes")


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: uv run tools/portrait.py <source-image> <slug>")
    src, slug = Path(sys.argv[1]), sys.argv[2]
    # Read fully into memory so the source may be overwritten.
    with Image.open(io.BytesIO(src.read_bytes())) as raw:
        img = crop_4x5(raw.convert("RGB"))
    save(img, ROOT / f"{slug}.webp", (400, 500))
    save(img, ROOT / "thumbs" / f"{slug}.webp", (80, 100))


if __name__ == "__main__":
    main()
