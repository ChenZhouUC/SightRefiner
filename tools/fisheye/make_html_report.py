#!/usr/bin/env python3
"""Generate data/fisheye/batches/<batch>/report/REPORT_EN.html as a
self-contained English HTML report (single file, all imagery embedded as base64).

Run after tools/fisheye/make_report.py. Output is gitignored and stays with
the batch report data.

Usage:
  python tools/fisheye/make_html_report.py [batch_id]
"""

import base64
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_BATCH = "2026-08-10_pilot_camera_scrnsht"

PREFERRED_FEATURED = [
    "2564_San_Jose_Market_Center_cam03.png",
    "398_Union_Square_cam05.png",
    "1272_Southport_cam02.png",
]

CSS = """
:root { --fg:#16181d; --muted:#5f6672; --line:#e5e8ec; --accent:#0b6bcb;
        --soft:#f7f9fb; }
* { box-sizing:border-box; }
body { margin:0; color:var(--fg); background:#fff;
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
main { max-width:1080px; margin:0 auto; padding:0 28px 90px; }
header { padding:64px 0 28px; }
h1 { font-size:2.3rem; line-height:1.2; margin:0 0 10px; letter-spacing:-.01em; }
.sub { font-size:1.15rem; color:var(--muted); max-width:62ch; }
h2 { font-size:1.5rem; margin:2.6em 0 .5em; letter-spacing:-.01em; }
p { max-width:72ch; }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:14px; margin:26px 0 8px; }
.kpis div { border:1px solid var(--line); border-radius:12px; padding:18px 20px;
  background:var(--soft); }
.kpis b { display:block; font-size:2rem; line-height:1.15; color:var(--accent); }
.kpis span { color:var(--muted); font-size:.9rem; }
.steps { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
  gap:14px; margin:18px 0; counter-reset:step; }
.steps div { border:1px solid var(--line); border-radius:12px; padding:16px 18px; }
.steps div::before { counter-increment:step; content:counter(step);
  display:inline-flex; width:26px; height:26px; border-radius:50%;
  background:var(--accent); color:#fff; font-weight:700; font-size:.9rem;
  align-items:center; justify-content:center; margin-bottom:8px; }
.steps b { display:block; margin-bottom:4px; }
.steps span { color:var(--muted); font-size:.92rem; }
img { max-width:100%; height:auto; border:1px solid var(--line);
  border-radius:8px; display:block; }
figure { margin:1.2em 0 2em; }
figcaption { color:var(--muted); font-size:.9rem; margin-top:8px; }
.dims { display:inline-block; margin-top:8px; padding:6px 8px; color:#102a43;
  background:#eef6ff; border:1px solid #badbff; border-radius:6px; font-size:.9rem;
  font-weight:600; font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace; }
details { border:1px solid var(--line); border-radius:12px;
  padding:12px 18px; margin:14px 0; }
summary { cursor:pointer; font-weight:600; font-size:1.06rem; }
summary span { color:var(--muted); font-weight:400; font-size:.9rem; }
.note { background:var(--soft); border:1px solid var(--line); border-radius:12px;
  padding:14px 18px; color:var(--muted); font-size:.93rem; max-width:none; }
.small { font-size:.88rem; color:var(--muted); }
"""


def img64(path):
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()


def format_dims(stats):
    if not stats or "dimensions" not in stats:
        return ""
    d = stats["dimensions"]
    order = ["source", "panorama", "view0", "view1", "view2", "view3"]
    parts = []
    for key in order:
        if key in d:
            w, h = d[key]
            label = "source" if key == "source" else key
            parts.append(f"{label}: {w}x{h}px")
    return "<span class='dims'>Dimensions: " + " | ".join(parts) + "</span>"


def figure(name, caption, stats=None):
    jpg = os.path.join(REPORT_DIR, "samples", name.replace(".png", ".jpg"))
    return f"<figure><img loading='lazy' src='{img64(jpg)}' alt='{name}'><figcaption>{caption}{format_dims(stats)}</figcaption></figure>"


def sample_site_id(sample):
    return sample.get("site", {}).get("id") or sample.get("store", "")


def main():
    global MODULE_DATA_DIR, REPORT_DIR, OUT
    batch = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BATCH
    MODULE_DATA_DIR = os.path.join(ROOT, "data", "fisheye", "batches", batch)
    REPORT_DIR = os.path.join(MODULE_DATA_DIR, "report")
    OUT = os.path.join(REPORT_DIR, "REPORT_EN.html")
    summary = json.load(open(os.path.join(REPORT_DIR, "summary.json")))
    meta = json.load(open(os.path.join(MODULE_DATA_DIR, "images", "meta.json")))
    stats_by_name = {s["name"]: s for s in summary["samples"]}
    bench = summary["benchmark"]
    n = summary["n_samples"]

    sites = {}
    for name, m in sorted(meta.items()):
        sites.setdefault(sample_site_id(m), []).append(name)
    site_order = sorted(sites, key=lambda s: -len(sites[s]))
    site_count = len(sites)
    available_names = sorted(meta)
    featured = [name for name in PREFERRED_FEATURED if name in meta]
    featured.extend(name for name in available_names if name not in featured)
    featured = featured[: min(3, len(featured))]

    cap = (
        "Top: 360&deg; panorama. Bottom: source fisheye image "
        "(green = auto-detected lens circle) and four dewarped perspective views "
        "at 90&deg; azimuth intervals."
    )

    featured_html = "\n".join(
        figure(f, f"<b>{f.replace('.png', '').replace('_', ' ')}</b> - {cap}", stats_by_name.get(f)) for f in featured
    )

    gallery = []
    for site in site_order:
        pretty = site.replace("_", " ")
        gallery.append(f"<details><summary>{pretty} <span>- {len(sites[site])} cameras</span></summary>")
        for nm in sites[site]:
            gallery.append(figure(nm, f"<code>{nm.replace('.png', '')}</code>", stats_by_name.get(nm)))
        gallery.append("</details>")
    gallery_html = "\n".join(gallery)

    body = f"""
<header>
<h1>Fisheye Dewarp Test Report</h1>
<p class="sub">This report validates one complete batch path: raw materials are adapted into
standard site/camera test inputs, then each fisheye sample is auto-calibrated and dewarped into
a 360&deg; panorama plus four perspective views. All report images are embedded in this single HTML
file.</p>
</header>

<div class="kpis">
<div><b>{n}</b><span>standardized fisheye samples processed</span></div>
<div><b>{site_count}</b><span>sites covered through explicit site/camera metadata</span></div>
<div><b>{summary["n_fallback"]}</b><span>calibration fallbacks used after automatic circle detection</span></div>
<div><b>{bench["remap_ms_per_frame_total"]} ms</b><span>benchmark remap time per frame on this host</span></div>
</div>

<h2>Pipeline</h2>
<div class="steps">
<div><b>Adapt raw</b><span>A batch-local script parses the current raw layout and emits the
standard test input: images plus meta.json grouped by site and camera.</span></div>
<div><b>Auto-calibrate</b><span>The fisheye helper reads only the standard input and locates the
lens circle for each sample, falling back to metadata only if detection fails.</span></div>
<div><b>Freeze</b><span>The calibration is compiled once into a compact lookup table
({bench["lut_npz_mb"]} MB per camera). From then on, nothing needs to be computed again.</span></div>
<div><b>Run on the edge</b><span>Each incoming frame is remapped through the table in
{bench["remap_ms_per_frame_total"]} ms into a 360&deg; overview panorama plus four normal-looking
views for downstream analytics.</span></div>
</div>
<p class="note">The heavily warped outer rim and the smeared spot directly under the camera are
intentionally cropped away, keeping the parts where people are recognizable.</p>

<h2>Highlights</h2>
<p>Each composite shows the source frame, generated panorama and four perspective views. Pixel
dimensions are printed both inside the image and in the caption.</p>
{featured_html}

<h2>All Samples ({n} across {site_count} sites)</h2>
<p>Full results are grouped by site. Every normalized fisheye sample in this batch was processed
through the same standard-input pipeline. Click a site to expand.</p>
{gallery_html}

<h2>Report Contract</h2>
<p>The HTML is self-contained: all {n} result images are embedded as base64 data URLs, with no
relative image, CSS or JavaScript dependencies. Batch-specific raw parsing remains outside the
public test contract; the public contract starts at images/ and ends at report/.</p>
"""

    html = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Fisheye Dewarp Test Report</title>"
        f"<style>{CSS}</style></head><body><main>{body}</main></body></html>"
    )
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(OUT, "w") as f:
        f.write(html)
    print(f"{OUT}: {os.path.getsize(OUT) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
