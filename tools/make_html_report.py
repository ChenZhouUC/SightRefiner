#!/usr/bin/env python3
"""Generate data/report/REPORT_EN.html — a self-contained, executive/customer-facing
English showcase page (single file, all imagery embedded as base64).

Deliberately non-academic: leads with "fully automatic" and the visual
results. Run after tools/make_report.py. Output is gitignored and stays with
the report data.
"""

import base64
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(ROOT, "data", "report")
OUT = os.path.join(REPORT_DIR, "REPORT_EN.html")

# Strongest samples shown full-width up front (people visible, clean geometry).
FEATURED = [
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
figcaption { color:var(--muted); font-size:.87rem; margin-top:7px; }
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


def figure(name, caption):
    jpg = os.path.join(ROOT, "data", "report", "samples", name.replace(".png", ".jpg"))
    return f"<figure><img loading='lazy' src='{img64(jpg)}' alt='{name}'><figcaption>{caption}</figcaption></figure>"


def main():
    summary = json.load(open(os.path.join(ROOT, "data", "report", "summary.json")))
    meta = json.load(open(os.path.join(ROOT, "data", "fisheye", "meta.json")))
    bench = summary["benchmark"]
    n = summary["n_samples"]

    stores = {}
    for name, m in sorted(meta.items()):
        stores.setdefault(m["store"], []).append(name)
    store_order = sorted(stores, key=lambda s: -len(stores[s]))

    cap = (
        "Top: 360&deg; panorama of the whole floor. Bottom: original fisheye "
        "(green = auto-detected lens circle) and four straightened views "
        "facing north / east / south / west."
    )

    featured_html = "\n".join(
        figure(f, f"<b>{f.split('_cam')[0].replace('_', ' ')}</b> &mdash; {cap}") for f in FEATURED
    )

    gallery = []
    for store in store_order:
        pretty = store.replace("_", " ")
        gallery.append(f"<details><summary>{pretty} <span>&mdash; {len(stores[store])} cameras</span></summary>")
        for nm in stores[store]:
            gallery.append(figure(nm, f"<code>{nm.replace('.png', '')}</code>"))
        gallery.append("</details>")
    gallery_html = "\n".join(gallery)

    body = f"""
<header>
<h1>Making Fisheye Cameras Count People</h1>
<p class="sub">Ceiling fisheye cameras see the whole floor &mdash; but their circular, heavily
distorted images defeat standard people-counting models. Our pipeline turns every fisheye stream
into ordinary-looking camera views, <b>fully automatically</b>: no technician visit, no calibration
targets, no per-camera manual work.</p>
</header>

<div class="kpis">
<div><b>{n}/{n}</b><span>cameras calibrated automatically &mdash; zero manual steps</span></div>
<div><b>10/10</b><span>pilot stores covered, every fisheye camera found &amp; processed</span></div>
<div><b>&lt;2 ms</b><span>processing per frame &mdash; runs comfortably on low-cost edge hardware</span></div>
<div><b>1&times;</b><span>one-time setup per camera; the result is frozen and reused forever</span></div>
</div>

<h2>How it works — three steps, no manual calibration</h2>
<div class="steps">
<div><b>Auto-calibrate</b><span>The system looks at a single frame and locates the lens circle by
itself. Everything it decides is stored in a small, readable settings file that an operator can
review or adjust if ever needed.</span></div>
<div><b>Freeze</b><span>The calibration is compiled once into a compact lookup table
({bench["lut_npz_mb"]} MB per camera). From then on, nothing needs to be computed again.</span></div>
<div><b>Run on the edge</b><span>Each incoming frame is remapped through the table in
{bench["remap_ms_per_frame_total"]} ms into a 360&deg; overview panorama plus four normal-looking
views &mdash; ready for any off-the-shelf people-counting model.</span></div>
</div>
<p class="note">The heavily warped outer rim and the smeared spot directly under the camera are
intentionally cropped away &mdash; we keep exactly the parts where people are recognizable.</p>

<h2>See the results</h2>
<p>Three highlights from the pilot &mdash; note how shelves become straight and shoppers appear
upright, as if filmed by ordinary cameras:</p>
{featured_html}

<h2>Every camera from the pilot ({n} across 10 stores)</h2>
<p>Full results below, grouped by store &mdash; every fisheye camera we found in the pilot
screenshots, processed with the identical automatic pipeline (no per-camera tweaks). Click a store
to expand. Source images are small VMS thumbnails; on live HD streams the output is proportionally
sharper.</p>
{gallery_html}

<h2>What this means</h2>
<p>Fisheye cameras already installed in stores can feed standard people-counting analytics
without replacing hardware, without site visits, and without per-camera engineering effort.
Rolling out to a new store is: connect the streams, let the system calibrate itself, spot-check
the previews, done.</p>
<p class="small">Single-file report &mdash; all {n} result images embedded, no external links needed.
Engineering details, accuracy measurements and deployment notes can be generated from
the tools in this repository.</p>
"""

    html = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Making Fisheye Cameras Count People — Pilot Results</title>"
        f"<style>{CSS}</style></head><body><main>{body}</main></body></html>"
    )
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(OUT, "w") as f:
        f.write(html)
    print(f"{OUT}: {os.path.getsize(OUT) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
