#!/usr/bin/env python3
"""
Resize images in `images/` and `logo/` to create small/medium/large JPEG and WebP variants.
Usage:
  python scripts/resize_images.py

Requirements: Pillow (see requirements.txt)

This script will:
- For each .jpg/.jpeg/.png in images/: create -small.jpg (480w), -medium.jpg (800w), -large.jpg (1200w)
  and corresponding .webp files.
- For each logo image in logo/: create @2x PNG (2x scaled) and a webp if applicable.

Files are written next to the originals.
"""
from PIL import Image
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / 'images'
LOGO_DIR = ROOT / 'logo'

SIZES = [
    ('small', 480),
    ('medium', 800),
    ('large', 1200),
]

def ensure_dir(p: Path):
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)


def process_image(path: Path):
    if path.suffix.lower() not in ('.jpg', '.jpeg', '.png'):
        return
    try:
        img = Image.open(path).convert('RGB')
    except Exception as e:
        print(f"Skipping {path}: {e}")
        return

    for name, w in SIZES:
        ratio = w / img.width
        h = int(img.height * ratio)
        resized = img.resize((w, h), Image.LANCZOS)
        out_jpg = path.with_name(f"{path.stem}-{name}.jpg")
        resized.save(out_jpg, format='JPEG', quality=86, optimize=True)
        out_webp = out_jpg.with_suffix('.webp')
        resized.save(out_webp, format='WEBP', quality=80, optimize=True)
        print(f"Wrote: {out_jpg} and {out_webp}")


def process_logo(path: Path):
    if path.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
        return
    try:
        img = Image.open(path).convert('RGBA' if path.suffix.lower()=='.png' else 'RGB')
    except Exception as e:
        print(f"Skipping {path}: {e}")
        return

    # create 2x version (double the pixel density)
    w2 = img.width * 2
    h2 = img.height * 2
    resized = img.resize((w2, h2), Image.LANCZOS)
    out_png = path.with_name(f"{path.stem}@2x.png")
    # save as PNG to preserve transparency if present
    resized.save(out_png, format='PNG', optimize=True)
    print(f"Wrote logo 2x: {out_png}")
    # also write webp fallback (flatten if RGBA)
    if img.mode == 'RGBA':
        bg = Image.new('RGB', resized.size, (0,0,0))
        bg.paste(resized, mask=resized.split()[3])
        webp_out = path.with_name(f"{path.stem}@2x.webp")
        bg.save(webp_out, format='WEBP', quality=80, optimize=True)
        print(f"Wrote logo webp: {webp_out}")
    else:
        webp_out = path.with_name(f"{path.stem}@2x.webp")
        resized.convert('RGB').save(webp_out, format='WEBP', quality=80, optimize=True)
        print(f"Wrote logo webp: {webp_out}")


def main():
    ensure_dir(IMG_DIR)
    ensure_dir(LOGO_DIR)

    for p in sorted(IMG_DIR.iterdir()):
        process_image(p)

    for p in sorted(LOGO_DIR.iterdir()):
        process_logo(p)

    print('Done.')

if __name__ == '__main__':
    main()
