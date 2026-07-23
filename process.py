#!/usr/bin/env python3
"""Whiten bg -> trim -> center-pad each product shot onto a uniform white square tile."""
import os
import subprocess
import tempfile
from PIL import Image, ImageChops

SRC = "/Users/peterhigney/Library/CloudStorage/GoogleDrive-peter@higneyintl.com/Shared drives/1.0 MARKETING/Website/Product Realized white back drop"
OUT = "/Users/peterhigney/higney-website/assets/product-realized"
CANVAS = 1200          # square tile edge
OCCUPANCY = 0.82       # product's longest side as fraction of canvas
THRESH = 22            # diff-from-white threshold for content bbox

SELECT = {
    "1b547ff0-dfbd-4839-aeb1-0b9e280ec04b.jpeg": "sculpted-wood-side-table.jpg",
    "1cd86c41-760e-4e18-a6b6-9f1e517514a7.jpeg": "teak-high-chair.jpg",
    "402f6a45-4a26-4174-928f-289be4606ae8.jpeg": "teak-barrel-chair.jpg",
    "4d07f6ea-bd1a-41c0-9c48-214ab7d5ee82.jpeg": "woven-lounge-chair-grey.jpg",
    "4f78decf-4bd7-4dca-9bb0-b1917d5301d7.jpeg": "cane-dining-chair.jpg",
    "6c751398-1563-4c00-a4ed-dbf1b52f3a3d.jpeg": "wicker-club-chair.jpg",
    "IMG_0176.jpeg": "teak-pedestal-table.jpg",
    "abc0c2ca-24f0-4bd0-b7b1-04d31cd13ed5.jpeg": "travertine-coffee-table.jpg",
    "e718c01e-ab72-4377-b2b1-fc85f99b7c81.jpeg": "leather-seat-dining-chair.jpg",
    "DSCF5400.jpg": "woven-lounge-chair-ivory.jpg",
    "Juni-09781 (1).jpg": "sun-lounger-grey.jpg",
    "Juni-1110489.jpg": "live-edge-stool.jpg",
    "Juni-5670.jpg": "pedestal-stool.jpg",
    "SUN LOUNGER-2-2.jpg": "sun-lounger-white.jpg",
    # wave 2 (2026-07-22): new drops from the Drive folder
    "11be0675-4f59-44f0-89f9-35ba89a110ef.jpeg": "kidney-coffee-table.jpg",
    "2814a2e2-9b9d-4efa-8aca-7c45808b1842.jpg": "boucle-chaise.jpg",
    "68c6bcd6-f4c7-4fbe-affa-153097ebcf20.jpeg": "walnut-frame-sofa.jpg",
    "80e9f0eb-cdc7-4895-ba13-5646d09c25eb.jpeg": "teak-dining-table.jpg",
    "becbe6a4-2f30-43a8-8ebd-bf874e3bba7b.jpg": "round-ottoman.jpg",
    "cad25922-3087-4d44-93cf-3c107e14471f.jpg": "upholstered-pouf.jpg",
    "d36f6e7c-88fe-493e-9a61-b918adf3a901.jpeg": "cane-armchair.jpg",
    "e0a653f0-5075-413b-8276-97fb51ede79f.jpg": "oak-side-table.jpg",
    "ffaf1a3f-3742-4b45-acdb-c81f80771498.jpeg": "walnut-frame-armchair.jpg",
}

# shots against the dark grey plaster studio wall — levels-stretch can't whiten those
# without blowing out the products, so cut the subject onto white first
# (macOS 14 Vision subject lift, see lift.swift)
LIFT = {
    "2814a2e2-9b9d-4efa-8aca-7c45808b1842.jpg",
    "becbe6a4-2f30-43a8-8ebd-bf874e3bba7b.jpg",
    "cad25922-3087-4d44-93cf-3c107e14471f.jpg",
    "e0a653f0-5075-413b-8276-97fb51ede79f.jpg",
}

def corner_bg(img):
    """Median bright-pixel color across the four corner patches."""
    w, h = img.size
    p = max(8, min(w, h) // 20)
    samples = []
    for box in [(0, 0, p, p), (w - p, 0, w, p), (0, h - p, p, h), (w - p, h - p, w, h)]:
        px = list(img.crop(box).getdata())
        samples += [c for c in px if min(c) > 200]
    if not samples:
        return (250, 250, 250)
    samples.sort()
    return samples[len(samples) // 2]

def process(src_path, out_path):
    img = Image.open(src_path).convert("RGB")
    # shrink giant camera files first so bbox math is fast and output is web-sized
    if max(img.size) > 2400:
        img.thumbnail((2400, 2400), Image.LANCZOS)
    bg = corner_bg(img)
    # levels stretch: push the background to pure white, gain capped to avoid blowout
    gains = [min(255.0 / max(c, 1), 1.4) for c in bg]
    lut = []
    for g in gains:
        lut += [min(255, round(i * g)) for i in range(256)]
    img = img.point(lut)
    diff = ImageChops.difference(img, Image.new("RGB", img.size, (255, 255, 255)))
    mask = diff.convert("L").point(lambda p: 255 if p > THRESH else 0)
    bbox = mask.getbbox()
    if bbox is None:
        bbox = (0, 0, img.size[0], img.size[1])
    # small breathing margin around the content
    m = round(0.015 * max(img.size))
    bbox = (max(0, bbox[0] - m), max(0, bbox[1] - m),
            min(img.size[0], bbox[2] + m), min(img.size[1], bbox[3] + m))
    img = img.crop(bbox)
    target = round(CANVAS * OCCUPANCY)
    scale = target / max(img.size)
    img = img.resize((max(1, round(img.size[0] * scale)),
                      max(1, round(img.size[1] * scale))), Image.LANCZOS)
    tile = Image.new("RGB", (CANVAS, CANVAS), (255, 255, 255))
    tile.paste(img, ((CANVAS - img.size[0]) // 2, (CANVAS - img.size[1]) // 2))
    tile.save(out_path, "JPEG", quality=86, optimize=True)

os.makedirs(OUT, exist_ok=True)
for src, dst in SELECT.items():
    sp = os.path.join(SRC, src)
    if src in LIFT:
        lifted = os.path.join(tempfile.gettempdir(), "lifted-" + src + ".jpg")
        subprocess.run(["swift", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "lift.swift"), sp, lifted], check=True)
        sp = lifted
    process(sp, os.path.join(OUT, dst))
    print("tile:", dst)

# hero: wide crop of the in-situ scene shot, web-sized (no whitening)
hero = Image.open(os.path.join(SRC, "IMG_0393.jpeg")).convert("RGB")
hero.thumbnail((2200, 2200), Image.LANCZOS)
hero.save(os.path.join(OUT, "hero-product-scene.jpg"), "JPEG", quality=84, optimize=True)
print("hero:", "hero-product-scene.jpg", hero.size)
