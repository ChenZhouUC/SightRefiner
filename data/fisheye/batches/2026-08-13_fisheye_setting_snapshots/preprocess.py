#!/usr/bin/env python3
"""Build standard fisheye test inputs for this batch from raw snapshot folders."""

from pathlib import Path
import json
import re
import shutil
import sys

import cv2

BATCH_DIR = Path(__file__).resolve().parent
ROOT = BATCH_DIR.parents[3]
RAW_DIR = BATCH_DIR / "raw"
IMAGES_DIR = BATCH_DIR / "images"
IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
SKIP_NAME_PARTS = ("spec", "setting")

sys.path.insert(0, str(ROOT))

from sightrefiner.fisheye import detect_image_circle


def slugify(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", value).strip("_")


def strip_timestamp(stem: str) -> str:
    return re.sub(r"[_-]20\d{2}[_-]\d{2}[_-]\d{2}[_-]\d{2}[_-]\d{2}[_-]\d{2}$", "", stem)


def raw_images():
    for path in sorted(RAW_DIR.rglob("*")):
        if path.name.startswith(".") or not path.is_file():
            continue
        if path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def is_reference_image(path: Path) -> bool:
    lowered = path.name.lower()
    return any(part in lowered for part in SKIP_NAME_PARTS)


def unique_name(name: str, used: set[str]) -> str:
    if name not in used:
        used.add(name)
        return name
    stem = Path(name).stem
    suffix = Path(name).suffix
    i = 2
    while True:
        candidate = f"{stem}_{i:02d}{suffix}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        i += 1


def main() -> None:
    if IMAGES_DIR.exists():
        shutil.rmtree(IMAGES_DIR)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    meta = {}
    used_names: set[str] = set()
    skipped = 0
    for path in raw_images():
        if is_reference_image(path):
            skipped += 1
            continue

        img = cv2.imread(str(path))
        if img is None:
            skipped += 1
            continue

        try:
            cx, cy, r = detect_image_circle(img)
        except ValueError:
            skipped += 1
            continue

        rel = path.relative_to(RAW_DIR)
        site_id = slugify(rel.parts[0]) if len(rel.parts) > 1 else "unknown_site"
        camera_id = slugify(strip_timestamp(path.stem))
        name = unique_name(f"{site_id}_{camera_id}.png", used_names)
        cv2.imwrite(str(IMAGES_DIR / name), img)

        source_file = str(path.relative_to(BATCH_DIR))
        bbox = [0, 0, int(img.shape[1]), int(img.shape[0])]
        meta[name] = {
            "site": {"id": site_id},
            "camera": {"id": camera_id},
            "circle": {"cx": float(cx), "cy": float(cy), "r": float(r)},
            "source": {"file": source_file, "bbox": bbox},
        }
        print(f"{source_file}: fisheye snapshot -> {name}")

    with open(IMAGES_DIR / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"total: {len(meta)} fisheye samples -> {IMAGES_DIR}; skipped: {skipped}")


if __name__ == "__main__":
    main()
