"""One-time per-camera auto-calibration.

Input: one (or a few) raw frames from the camera — a circular fisheye image
surrounded by black. Output: a CameraProfile JSON that a human can inspect,
correct, and freeze.

Method (deliberately simple and auditable):
  1. threshold the frame to get the bright content mask;
  2. Kasa least-squares circle fit on the mask contour for an initial circle;
  3. refine per-angle: along each radial ray find the outermost strong
     brightness drop into darkness (the physical image-circle edge), then take
     the median radius over all angles that produced a consistent edge.
The FOV cannot be observed from a single frame without scene assumptions, so
it defaults to 180 deg (surveillance-lens standard) and stays a human-editable
field in the profile.
"""

from __future__ import annotations

import numpy as np
import cv2

from .model import CameraProfile

EDGE_DROP = 15.0  # min outward brightness drop that counts as the circle edge


def detect_image_circle(img: np.ndarray):
    """Return (cx, cy, r) of the fisheye image circle in a raw frame.

    Works on frames where the circular image sits on a (near-)black surround.
    Raises ValueError when no plausible circle is found — callers should then
    fall back to a manually specified circle in the profile.
    """
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    m = (gray > 25).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError("no content found in frame")
    pts = max(contours, key=cv2.contourArea).reshape(-1, 2).astype(np.float64)
    # frame-border points belong to clipping, not the circle edge
    inner = pts[(pts[:, 0] > 3) & (pts[:, 0] < w - 4) & (pts[:, 1] > 3) & (pts[:, 1] < h - 4)]
    if len(inner) < 30:
        raise ValueError("content boundary hugs the frame border everywhere")
    A = np.c_[2 * inner[:, 0], 2 * inner[:, 1], np.ones(len(inner))]
    b = inner[:, 0] ** 2 + inner[:, 1] ** 2
    (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    r0 = float(np.sqrt(max(c + cx * cx + cy * cy, 1.0)))

    # refine radius on the outermost content->black transition per ray
    blur = cv2.GaussianBlur(gray, (5, 5), 1.2).astype(np.float32)
    radii = []
    for a in np.linspace(0.0, 2.0 * np.pi, 360, endpoint=False):
        ca, sa = np.cos(a), np.sin(a)
        rs = np.arange(0.7 * r0, 1.3 * r0, 1.0)
        xs, ys = cx + rs * ca, cy + rs * sa
        ok = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
        if ok.sum() < 12:
            continue
        prof = blur[ys[ok].astype(int), xs[ok].astype(int)]
        drops = prof[:-4] - prof[4:]
        cand = np.where((drops >= EDGE_DROP) & (prof[4:] < 30))[0]
        if len(cand) == 0:
            continue
        radii.append(rs[ok][int(cand[-1]) + 2])
    if len(radii) < 60:
        raise ValueError("could not lock onto a circular image boundary")
    r = float(np.median(np.asarray(radii)))
    return float(cx), float(cy), r


def auto_profile(
    img: np.ndarray,
    camera_id: str,
    fov_deg: float = 180.0,
    mount: str = "ceiling",
    views=None,
) -> CameraProfile:
    """Build a reviewable profile for one camera from a raw frame."""
    cx, cy, r = detect_image_circle(img)
    profile = CameraProfile(
        camera_id=camera_id,
        image_size=[int(img.shape[1]), int(img.shape[0])],
        circle={"cx": round(cx, 2), "cy": round(cy, 2), "r": round(r, 2)},
        fov_deg=fov_deg,
        mount=mount,
    )
    if views is not None:
        profile.views = views
    return profile
