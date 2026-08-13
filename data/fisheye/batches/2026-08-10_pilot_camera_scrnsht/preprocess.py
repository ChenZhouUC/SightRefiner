#!/usr/bin/env python3
"""Preprocess xlsx VMS screenshots into the standard fisheye test input.

This is a batch-preprocessing helper, not the public test-data contract.
The public contract starts after preprocessing, at:
  data/fisheye/batches/<batch>/images/*.png
  data/fisheye/batches/<batch>/images/meta.json

The xlsx contains one sheet per store; each sheet embeds one screenshot of a
multi-camera VMS layout. Camera tiles sit on a near-black canvas, separated by
black gaps. We segment tiles with a recursive XY-cut over the brightness mask,
then classify each tile as fisheye (circular image, black corners, one sharp
circular edge at a consistent radius) vs standard rectangular video.

Outputs:
  data/fisheye/batches/<batch>/raw/<store>.png
                                        full screenshot per store
  data/fisheye/batches/<batch>/images/<store>_cam<k>.png
                                        tile crop per detected fisheye camera
  data/fisheye/batches/<batch>/images/meta.json
                                        per-crop circle center/radius (crop coords)

These extracted samples are local test data and are intentionally gitignored.

Usage:
  uv run python data/fisheye/batches/2026-08-10_pilot_camera_scrnsht/preprocess.py
  uv run python data/fisheye/batches/2026-08-10_pilot_camera_scrnsht/preprocess.py <xlsx_path>
"""

import json
import os
import re
import sys
import zipfile

import cv2
import numpy as np

MIN_TILE = 150  # px, min tile side to consider
MIN_RADIUS = 70  # px, min fisheye circle radius
BORDER_PAD = 9  # px, ignore tile selection frames drawn by the VMS
EDGE_DROP = 15  # min outward brightness drop that counts as the circle edge
BATCH_DIR = os.path.dirname(os.path.abspath(__file__))

# Human-reviewed rejects: tiles the detector accepts but visual review showed
# to be rectangular videos whose shadow pattern mimics an inscribed circle.
# Keyed by (store_slug, leaf_x0, leaf_y0) — stable for a given input xlsx.
REVIEW_BLACKLIST: set = set()


def slugify(name: str) -> str:
    name = re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_")
    return name


def sheet_image_pairs(xlsx_path):
    """Yield (sheet_name, png_bytes) by walking workbook -> sheet -> drawing rels."""
    with zipfile.ZipFile(xlsx_path) as z:
        wb = z.read("xl/workbook.xml").decode()
        wbrels = z.read("xl/_rels/workbook.xml.rels").decode()
        rid2sheet = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="worksheets/(sheet\d+\.xml)"', wbrels))
        for m in re.finditer(r'<sheet name="([^"]+)"[^>]*r:id="(rId\d+)"', wb):
            name, rid = m.group(1), m.group(2)
            name = re.sub(r"_x([0-9A-Fa-f]{4})_", lambda g: chr(int(g.group(1), 16)), name)
            sheetfile = rid2sheet.get(rid)
            if not sheetfile:
                continue
            try:
                srels = z.read(f"xl/worksheets/_rels/{sheetfile}.rels").decode()
            except KeyError:
                continue
            dm = re.search(r'Target="\.\./(drawings/drawing\d+\.xml)"', srels)
            if not dm:
                continue
            drels = z.read(f"xl/drawings/_rels/{os.path.basename(dm.group(1))}.rels").decode()
            im = re.search(r'Target="\.\./(media/image\d+\.\w+)"', drels)
            if not im:
                continue
            yield name, z.read(f"xl/{im.group(1)}")


def _content_runs(profile, span, min_gap=3):
    """Split a 1-D bright-pixel-count profile into runs separated by dark gaps.

    `span` is the length of the perpendicular axis; rows/cols carrying only a
    sliver of brightness (thin UI separators, stray markers) count as dark.
    """
    noise = max(2, int(0.03 * span))
    idx = np.where(profile > noise)[0]
    if len(idx) == 0:
        return []
    runs = []
    start = prev = idx[0]
    for i in idx[1:]:
        if i - prev > min_gap:
            runs.append((int(start), int(prev) + 1))
            start = i
        prev = i
    runs.append((int(start), int(prev) + 1))
    return runs


def _leaf_tiles(mask):
    """Recursive XY-cut: split at full-width/height dark gaps until atomic tiles."""
    H, W = mask.shape
    leaves = []
    stack = [(0, 0, W, H, 0)]
    while stack:
        x0, y0, x1, y1, depth = stack.pop()
        if x1 - x0 < MIN_TILE or y1 - y0 < MIN_TILE or depth > 8:
            continue
        sub = mask[y0:y1, x0:x1]
        rows = _content_runs(sub.sum(axis=1), x1 - x0)
        cols = _content_runs(sub.sum(axis=0), y1 - y0)
        if not rows or not cols:
            continue
        if len(rows) > 1:
            for r0, r1 in rows:
                stack.append((x0, y0 + r0, x1, y0 + r1, depth + 1))
        elif len(cols) > 1:
            for c0, c1 in cols:
                stack.append((x0 + c0, y0, x0 + c1, y1, depth + 1))
        else:
            r0, r1 = rows[0]
            c0, c1 = cols[0]
            trimmed = (x0 + c0, y0 + r0, x0 + c1, y0 + r1)
            if trimmed != (x0, y0, x1, y1):
                stack.append((*trimmed, depth + 1))  # re-check after border trim
            else:
                leaves.append(trimmed)
    return leaves


def _classify_fisheye(gray, box):
    """Return {'cx','cy','r'} in full-image coords if the tile holds a circular
    fisheye image, else None."""
    x0, y0, x1, y1 = box
    p = BORDER_PAD
    tile = gray[y0 + p : y1 - p, x0 + p : x1 - p]
    h, w = tile.shape
    if min(h, w) < MIN_TILE - 2 * p:
        return None
    m = (tile > 25).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    fill = float(m.mean())
    if not 0.30 < fill < 0.97:
        return None  # ~1.0 => rectangular video fills the tile

    # Initial circle from the content contour (Kasa least-squares fit on points
    # away from the tile border, so clipped circles fit correctly).
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    pts = max(contours, key=cv2.contourArea).reshape(-1, 2).astype(np.float64)
    inner = pts[(pts[:, 0] > 3) & (pts[:, 0] < w - 4) & (pts[:, 1] > 3) & (pts[:, 1] < h - 4)]
    if len(inner) < 30:
        return None
    A = np.c_[2 * inner[:, 0], 2 * inner[:, 1], np.ones(len(inner))]
    b = inner[:, 0] ** 2 + inner[:, 1] ** 2
    try:
        (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return None
    r0 = float(np.sqrt(max(c + cx * cx + cy * cy, 1.0)))
    if not MIN_RADIUS <= r0 <= 1.1 * max(h, w):
        return None

    # Refine + verify: along each radial ray, find the OUTERMOST strong
    # brightness drop that lands in darkness — the image-circle edge is the
    # last content→black transition, unlike shelf edges inside the scene.
    tile_f = cv2.GaussianBlur(tile, (5, 5), 1.2).astype(np.float32)
    radii = []
    for a in np.linspace(0.0, 2.0 * np.pi, 180, endpoint=False):
        ca, sa = np.cos(a), np.sin(a)
        rs = np.arange(0.60 * r0, 1.30 * r0, 1.0)
        xs, ys = cx + rs * ca, cy + rs * sa
        ok = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
        if ok.sum() < 12:
            continue
        prof = tile_f[ys[ok].astype(int), xs[ok].astype(int)]
        drops = prof[:-4] - prof[4:]  # brightness lost over a 4 px outward step
        cand = np.where((drops >= EDGE_DROP) & (prof[4:] < 30))[0]
        if len(cand) == 0:
            continue
        k = int(cand[-1])
        tail = prof[k + 4 :]
        if len(tail) >= 6 and (tail < 35).mean() < 0.7:
            continue  # brightens again further out: not the surround boundary
        radii.append(rs[ok][k + 2])
    if len(radii) < 40:
        return None
    radii = np.asarray(radii)
    r = float(np.median(radii))
    if (np.abs(radii - r) <= 4.0).mean() < 0.50 or r < MIN_RADIUS:
        return None

    # The VMS renders a fisheye stream as a circle centered in the tile and
    # scaled to (approximately) inscribe it. Phantom circles fitted to shadow
    # patterns inside rectangular videos are far larger than the tile.
    if abs(cx - w / 2) > max(8.0, 0.08 * w) or abs(cy - h / 2) > max(8.0, 0.08 * h):
        return None
    if not 0.80 <= 2 * r / min(y1 - y0, x1 - x0) <= 1.12:
        return None

    # Everything outside the circle must be black (circular image on a black
    # tile). Opening suppresses timestamp overlays; the top band is excluded
    # entirely because some layouts draw large timestamps across the corner.
    solid = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    yy, xx = np.mgrid[0:h, 0:w]
    outside = ((xx - cx) ** 2 + (yy - cy) ** 2 > (1.05 * r) ** 2) & (yy > 0.22 * h)
    if outside.sum() > 200 and float(solid[outside].mean()) > 0.15:
        return None

    return {"cx": float(cx + x0 + p), "cy": float(cy + y0 + p), "r": r}


def detect_fisheye_tiles(img):
    """Return list of dicts {cx, cy, r, box} for fisheye tiles in a screenshot."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = (gray > 22).astype(np.uint8)
    found = []
    for box in _leaf_tiles(mask):
        c = _classify_fisheye(gray, box)
        if c is not None:
            c["box"] = [int(v) for v in box]
            found.append(c)
    found.sort(key=lambda t: (t["cy"] // 200, t["cx"]))
    return found


def extract_from_xlsx(xlsx, module_data_dir):
    shot_dir = os.path.join(module_data_dir, "raw")
    fe_dir = os.path.join(module_data_dir, "images")
    os.makedirs(shot_dir, exist_ok=True)
    os.makedirs(fe_dir, exist_ok=True)

    meta = {}
    total = 0
    for sheet, png in sheet_image_pairs(xlsx):
        store = slugify(sheet)
        img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
        cv2.imwrite(os.path.join(shot_dir, f"{store}.png"), img)

        tiles = [t for t in detect_fisheye_tiles(img) if (store, t["box"][0], t["box"][1]) not in REVIEW_BLACKLIST]
        for k, t in enumerate(tiles, 1):
            x0, y0, x1, y1 = t["box"]
            crop = img[y0:y1, x0:x1]
            name = f"{store}_cam{k:02d}.png"
            camera_id = f"cam{k:02d}"
            cv2.imwrite(os.path.join(fe_dir, name), crop)
            meta[name] = {
                "site": {"id": store},
                "camera": {"id": camera_id},
                "source": {"file": os.path.join("raw", f"{store}.png"), "bbox": [x0, y0, x1, y1]},
                "circle": {"cx": t["cx"] - x0, "cy": t["cy"] - y0, "r": t["r"]},
            }
            total += 1
        print(f"{store}: {len(tiles)} fisheye tiles")

    with open(os.path.join(fe_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"total: {total} fisheye samples -> {fe_dir}")


def main():
    xlsx = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BATCH_DIR, "raw", "pilot_camera_scrnsht.xlsx")
    print(f"batch={os.path.basename(BATCH_DIR)} preprocess=xlsx_vms_grid raw_path={xlsx}")
    extract_from_xlsx(xlsx, BATCH_DIR)


if __name__ == "__main__":
    main()
