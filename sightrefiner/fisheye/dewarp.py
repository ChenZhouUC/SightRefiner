"""LUT baking and the per-frame runtime.

Calibration freezes into fixed-point remap tables (CV_16SC2 + CV_16UC1):
integer source coordinates plus interpolation weights. At runtime every frame
costs exactly one cv2.remap per view — no trig, no model evaluation. The .npz
of maps is the only artifact the edge device needs besides OpenCV.
"""

from __future__ import annotations

import numpy as np
import cv2

from .model import CameraProfile
from .projections import dirs_for_view


def build_maps(profile: CameraProfile):
    """Bake fixed-point remap LUTs for every view in the profile."""
    maps = {}
    for view in profile.views:
        mx, my = profile.rays_to_pixels(dirs_for_view(view))
        m1, m2 = cv2.convertMaps(mx, my, cv2.CV_16SC2)
        maps[view["name"]] = (m1, m2)
    return maps


def save_maps(maps, path: str) -> None:
    arrays = {}
    for name, (m1, m2) in maps.items():
        arrays[f"{name}__m1"] = m1
        arrays[f"{name}__m2"] = m2
    np.savez_compressed(path, **arrays)


def load_maps(path: str):
    data = np.load(path)
    names = sorted({k.rsplit("__", 1)[0] for k in data.files})
    return {n: (data[f"{n}__m1"], data[f"{n}__m2"]) for n in names}


class Dewarper:
    """Edge runtime: apply frozen LUTs to each incoming frame."""

    def __init__(self, maps_or_profile, interpolation=cv2.INTER_LINEAR):
        if isinstance(maps_or_profile, CameraProfile):
            self.maps = build_maps(maps_or_profile)
        elif isinstance(maps_or_profile, str):
            self.maps = load_maps(maps_or_profile)
        else:
            self.maps = maps_or_profile
        self.interpolation = interpolation

    def process(self, frame: np.ndarray):
        return {
            name: cv2.remap(
                frame,
                m1,
                m2,
                self.interpolation,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=0,
            )
            for name, (m1, m2) in self.maps.items()
        }
