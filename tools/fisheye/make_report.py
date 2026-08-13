#!/usr/bin/env python3
"""Run the full auto-calibration + dewarp pipeline over every extracted
fisheye sample and produce the report assets:

  data/fisheye/batches/<batch>/report/samples/<name>.jpg
                                    per-sample composite (source | panorama | 4 views)
  data/fisheye/batches/<batch>/report/views/<name>/
                                    source.png + panorama.png + view0.png..view3.png
  data/fisheye/batches/<batch>/report/summary.json
                                    calibration stats + runtime benchmark

Report output stays under data/<module>/batches/<batch>/report/ and is intentionally gitignored.
Views are sized relative to the source circle radius so the demo neither
upsamples nor hides detail; on production streams the same profile scales up.

Usage:
  python tools/fisheye/make_report.py [batch_id]
"""

import json
import os
import sys
import time

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from sightrefiner.fisheye import CameraProfile, Dewarper, build_maps, save_maps, detect_image_circle

PANO_THETA = [30.0, 85.0]  # keep: drop smeared zenith (<30) and extreme rim (>85)
VIEW_TILT = 50.0
VIEW_HFOV = 90.0
DEFAULT_BATCH = "2026-08-10_pilot_camera_scrnsht"


def sample_site_id(sample):
    return sample.get("site", {}).get("id") or sample.get("store", "")


def sample_camera_id(sample, fallback_name):
    return sample.get("camera", {}).get("id") or fallback_name.replace(".png", "")


def demo_views(r: float):
    pano_w = int(4.5 * r) // 4 * 4
    pano_h = max(48, int(pano_w * (PANO_THETA[1] - PANO_THETA[0]) / 360.0))
    vw, vh = int(1.9 * r) // 4 * 4, int(1.42 * r) // 4 * 4
    return [
        {"name": "panorama", "type": "panorama", "size": [pano_w, pano_h], "theta_deg": PANO_THETA, "phi0_deg": 0.0},
        *[
            {
                "name": f"view{k}",
                "type": "perspective",
                "size": [vw, vh],
                "hfov_deg": VIEW_HFOV,
                "azimuth_deg": az,
                "tilt_deg": VIEW_TILT,
            }
            for k, az in enumerate((0.0, 90.0, 180.0, 270.0))
        ],
    ]


def with_size(text, img):
    h, w = img.shape[:2]
    return f"{text}  {w}x{h}px"


def dims(img):
    h, w = img.shape[:2]
    return [int(w), int(h)]


def save_individual_views(report_dir, name, source, outs):
    stem = os.path.splitext(name)[0]
    rel_dir = os.path.join("views", stem)
    view_dir = os.path.join(report_dir, rel_dir)
    os.makedirs(view_dir, exist_ok=True)

    assets = {"source": os.path.join(rel_dir, "source.png")}
    cv2.imwrite(os.path.join(view_dir, "source.png"), source)

    for key in ["panorama", "view0", "view1", "view2", "view3"]:
        rel_path = os.path.join(rel_dir, f"{key}.png")
        cv2.imwrite(os.path.join(report_dir, rel_path), outs[key])
        assets[key] = rel_path

    return assets


def label(img, text):
    scale = max(0.7, min(4.5, img.shape[1] / 420.0))
    thickness = max(2, int(round(scale * 1.4)))
    margin = max(6, int(round(scale * 6)))
    (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    overlay = img.copy()
    cv2.rectangle(
        overlay,
        (0, 0),
        (tw + 2 * margin, th + baseline + 2 * margin),
        (0, 0, 0),
        -1,
    )
    cv2.addWeighted(overlay, 0.62, img, 0.38, 0, img)
    org = (margin, margin + th)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 3, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 255, 255), thickness, cv2.LINE_AA)
    return img


def composite(img, circle, outs):
    pano = outs["panorama"]
    views = [outs[f"view{k}"] for k in range(4)]
    vh = views[0].shape[0]

    src = img.copy()
    cv2.circle(src, (int(circle["cx"]), int(circle["cy"])), int(circle["r"]), (0, 255, 0), 2)
    s = vh / src.shape[0]
    src = cv2.resize(src, (int(src.shape[1] * s), vh))

    row = np.hstack(
        [label(src, with_size("source", img))]
        + [label(v.copy(), with_size(f"view{k} az={k * 90}", v)) for k, v in enumerate(views)]
    )
    W = row.shape[1]
    pano = cv2.resize(pano, (W, int(pano.shape[0] * W / pano.shape[1])))
    out = np.vstack(
        [
            label(pano, with_size(f"panorama 360deg theta {PANO_THETA[0]:.0f}-{PANO_THETA[1]:.0f}", outs["panorama"])),
            row,
        ]
    )
    return out


def benchmark(report_dir):
    """LUT bake + remap timing at a production-like resolution."""
    frame = np.random.randint(0, 255, (1920, 1920, 3), np.uint8)
    prof = CameraProfile(
        camera_id="bench",
        image_size=[1920, 1920],
        circle={"cx": 960.0, "cy": 960.0, "r": 940.0},
        views=[
            {"name": "panorama", "type": "panorama", "size": [1280, 384], "theta_deg": PANO_THETA, "phi0_deg": 0.0},
            *[
                {
                    "name": f"view{k}",
                    "type": "perspective",
                    "size": [640, 480],
                    "hfov_deg": VIEW_HFOV,
                    "azimuth_deg": az,
                    "tilt_deg": VIEW_TILT,
                }
                for k, az in enumerate((0.0, 90.0, 180.0, 270.0))
            ],
        ],
    )
    t0 = time.perf_counter()
    maps = build_maps(prof)
    bake_s = time.perf_counter() - t0
    npz = os.path.join(report_dir, "bench_maps.npz")
    save_maps(maps, npz)
    dw = Dewarper(maps)
    for _ in range(10):
        dw.process(frame)  # warmup
    n = 100
    t0 = time.perf_counter()
    for _ in range(n):
        dw.process(frame)
    per_frame_ms = (time.perf_counter() - t0) / n * 1000.0
    return {
        "input": "1920x1920 BGR",
        "outputs": "1x 1280x384 panorama + 4x 640x480 perspective",
        "lut_bake_s": round(bake_s, 3),
        "lut_npz_mb": round(os.path.getsize(npz) / 1e6, 2),
        "remap_ms_per_frame_total": round(per_frame_ms, 2),
        "host": "Apple Silicon macOS (single process; ARM edge SoC ~2-5x slower)",
    }


def main():
    batch = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BATCH
    module_data_dir = os.path.join(ROOT, "data", "fisheye", "batches", batch)
    fe_dir = os.path.join(module_data_dir, "images")
    report_dir = os.path.join(module_data_dir, "report")
    out_dir = os.path.join(report_dir, "samples")
    os.makedirs(out_dir, exist_ok=True)
    meta = json.load(open(os.path.join(fe_dir, "meta.json")))

    stats = []
    for name in sorted(meta):
        img = cv2.imread(os.path.join(fe_dir, name))
        ref = meta[name]["circle"]
        try:
            cx, cy, r = detect_image_circle(img)
            fallback = False
        except ValueError:
            cx, cy, r = ref["cx"], ref["cy"], ref["r"]
            fallback = True
        circle = {"cx": round(cx, 2), "cy": round(cy, 2), "r": round(r, 2)}
        prof = CameraProfile(
            camera_id=name.replace(".png", ""),
            image_size=[img.shape[1], img.shape[0]],
            circle=circle,
            views=demo_views(r),
        )
        outs = Dewarper(prof).process(img)
        assets = save_individual_views(report_dir, name, img, outs)
        sheet = composite(img, circle, outs)
        cv2.imwrite(os.path.join(out_dir, name.replace(".png", ".jpg")), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
        stats.append(
            {
                "name": name,
                "site": {"id": sample_site_id(meta[name])},
                "camera": {"id": sample_camera_id(meta[name], name)},
                "r_px": circle["r"],
                "center_delta_px": round(float(np.hypot(cx - ref["cx"], cy - ref["cy"])), 2),
                "radius_delta_px": round(float(abs(r - ref["r"])), 2),
                "calib_fallback": fallback,
                "dimensions": {
                    "source": dims(img),
                    "panorama": dims(outs["panorama"]),
                    **{f"view{k}": dims(outs[f"view{k}"]) for k in range(4)},
                },
                "assets": assets,
            }
        )
        print(f"{name}: r={r:.1f} d_center={stats[-1]['center_delta_px']:.2f} {'FALLBACK' if fallback else ''}")

    summary = {
        "n_samples": len(stats),
        "n_fallback": sum(s["calib_fallback"] for s in stats),
        "benchmark": benchmark(report_dir),
        "samples": stats,
    }
    with open(os.path.join(report_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary["benchmark"], indent=2))


if __name__ == "__main__":
    main()
