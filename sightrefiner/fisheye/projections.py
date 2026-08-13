"""Output projections: build per-pixel ray-direction grids in the camera frame.

Camera frame convention: +z along the optical axis into the scene (for a
ceiling mount, straight down at the floor), +x to the image right, +y to the
image bottom. Each builder returns an (H, W, 3) array of ray directions; the
camera model then converts rays to source-pixel coordinates.
"""

from __future__ import annotations

import numpy as np


def _rot_x(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _rot_z(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def perspective_dirs(size, hfov_deg: float, azimuth_deg: float, tilt_deg: float):
    """Virtual pinhole camera: `tilt` rotates the gaze away from the optical
    axis (0 = straight along it), `azimuth` chooses the compass direction.
    Image "up" points away from the fisheye nadir, so people stand upright."""
    w, h = size
    fp = (w / 2.0) / np.tan(np.deg2rad(hfov_deg) / 2.0)
    u, v = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    rays = np.stack([(u - w / 2.0) / fp, (v - h / 2.0) / fp, np.ones_like(u)], axis=-1)
    rays /= np.linalg.norm(rays, axis=-1, keepdims=True)
    rot = _rot_z(np.deg2rad(azimuth_deg)) @ _rot_x(np.deg2rad(tilt_deg))
    return rays @ rot.T


def panorama_dirs(size, theta_deg, phi0_deg: float = 0.0):
    """Cylindrical (equiangular) unwrap of the annulus theta in [t0, t1]:
    columns sweep azimuth 0..360deg, rows sweep polar angle t1 (top) down to
    t0 (bottom). Overhead geometry note: a standing person's head is at a
    LARGER polar angle than their feet (closer to the camera, same horizontal
    offset), so theta must decrease downward for people to appear upright."""
    w, h = size
    t0, t1 = np.deg2rad(theta_deg[0]), np.deg2rad(theta_deg[1])
    phi = np.deg2rad(phi0_deg) + 2.0 * np.pi * (np.arange(w) + 0.5) / w
    theta = t1 - (t1 - t0) * (np.arange(h) + 0.5) / h
    tt, pp = np.meshgrid(theta, phi, indexing="ij")
    return np.stack([np.sin(tt) * np.cos(pp), np.sin(tt) * np.sin(pp), np.cos(tt)], axis=-1)


def groundplane_dirs(size, radius_m: float, height_m: float = 3.0):
    """True bird's-eye view of the floor plane: orthographic top-down map of a
    disc of `radius_m` around the nadir, assuming camera height `height_m`.
    Useful for trajectory/zone analytics; stretch grows with radius."""
    w, h = size
    xs = (np.arange(w) + 0.5) / w * 2.0 - 1.0
    ys = (np.arange(h) + 0.5) / h * 2.0 - 1.0
    gx, gy = np.meshgrid(xs * radius_m, ys * radius_m)
    dirs = np.stack([gx, gy, np.full_like(gx, height_m)], axis=-1)
    return dirs / np.linalg.norm(dirs, axis=-1, keepdims=True)


def dirs_for_view(view: dict) -> np.ndarray:
    """Build the ray grid for one profile view entry."""
    t = view["type"]
    if t == "perspective":
        return perspective_dirs(view["size"], view["hfov_deg"], view["azimuth_deg"], view["tilt_deg"])
    if t == "panorama":
        return panorama_dirs(view["size"], view["theta_deg"], view.get("phi0_deg", 0.0))
    if t == "groundplane":
        return groundplane_dirs(view["size"], view["radius_m"], view.get("height_m", 3.0))
    raise ValueError(f"unknown view type: {t}")
