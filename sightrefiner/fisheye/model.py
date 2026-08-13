"""Camera model and per-camera profile.

The profile is the single human-editable artifact of calibration: plain JSON,
every field meaningful and overridable by hand. Once reviewed it is frozen and
compiled into remap LUTs (see dewarp.py) — nothing else ships to the edge.

Projection model: equidistant (f-theta), the de-facto standard for
surveillance fisheye lenses:  rho = f * theta,  f = R / theta_max
where R is the image-circle radius in pixels and theta_max = fov/2.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict

import numpy as np

DEFAULT_VIEWS = [
    {
        "name": "panorama",
        "type": "panorama",
        "size": [1024, 320],
        "theta_deg": [20.0, 80.0],
        "phi0_deg": 0.0,
    },
    *[
        {
            "name": f"view{k}",
            "type": "perspective",
            "size": [480, 360],
            "hfov_deg": 90.0,
            "azimuth_deg": az,
            "tilt_deg": 50.0,
        }
        for k, az in enumerate((0.0, 90.0, 180.0, 270.0))
    ],
]


@dataclass
class CameraProfile:
    camera_id: str
    image_size: list  # [w, h] of the raw frame
    circle: dict  # {"cx","cy","r"} image circle in raw-frame px
    model: str = "equidistant"
    fov_deg: float = 180.0  # full lens FOV across the image circle
    mount: str = "ceiling"  # ceiling | wall (documentation + view defaults)
    views: list = field(default_factory=lambda: [dict(v) for v in DEFAULT_VIEWS])

    @property
    def theta_max(self) -> float:
        return np.deg2rad(self.fov_deg) / 2.0

    @property
    def focal(self) -> float:
        return self.circle["r"] / self.theta_max

    def to_json(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def from_json(cls, path: str) -> "CameraProfile":
        with open(path) as f:
            return cls(**json.load(f))

    def rays_to_pixels(self, dirs: np.ndarray):
        """Project unit-ray directions (…x3, +z = optical axis) into the raw
        fisheye image. Returns float32 (map_x, map_y); rays outside the lens
        FOV map to (-1,-1) so cv2.remap paints them with the border color."""
        dx, dy, dz = dirs[..., 0], dirs[..., 1], dirs[..., 2]
        theta = np.arctan2(np.hypot(dx, dy), dz)
        phi = np.arctan2(dy, dx)
        rho = self.focal * theta
        mx = (self.circle["cx"] + rho * np.cos(phi)).astype(np.float32)
        my = (self.circle["cy"] + rho * np.sin(phi)).astype(np.float32)
        bad = theta > self.theta_max
        mx[bad] = -1.0
        my[bad] = -1.0
        return mx, my
