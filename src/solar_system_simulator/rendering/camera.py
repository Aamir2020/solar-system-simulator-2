"""Screen-space geometry, independent of Qt and the graphics context."""
import math
import numpy as np
from ..data.catalog import AU


class Camera:
    def __init__(self):
        self.center = np.zeros(2, dtype=np.float64)
        self.span = 5 * AU  # Full visible height in metres.
        self.target_center = self.center.copy()
        self.target_span = self.span

    def to_screen(self, positions, width, height):
        scale = height / self.span
        return (np.asarray(positions) - self.center) * [scale, -scale] + [width/2, height/2]

    def to_world(self, point, width, height):
        return self.center + (np.asarray(point) - [width/2, height/2]) * [1, -1] * self.span/height

    def zoom(self, point, factor, width, height):
        before = self.to_world(point, width, height)
        self.span = float(np.clip(self.span * factor, 0.00005 * AU, 160 * AU))
        after = self.to_world(point, width, height)
        self.center += before - after
        self.target_center = self.center.copy()
        self.target_span = self.span

    def pan(self, dx, dy, height):
        self.center += np.array([-dx, dy]) * self.span / max(height, 1)
        self.target_center = self.center.copy()

    def preset(self, center, span):
        self.target_center = np.array(center, dtype=np.float64, copy=True)
        self.target_span = float(np.clip(span, .00005 * AU, 160 * AU))

    def animate(self, dt, follow=None):
        if follow is not None:
            self.target_center = np.array(follow, dtype=np.float64, copy=True)
        alpha = 1 - math.exp(-min(dt, .1) * 10)
        self.center += (self.target_center - self.center) * alpha
        self.span += (self.target_span - self.span) * alpha


def pick_body(screen_positions, radii, point):
    distance = np.linalg.norm(screen_positions - np.asarray(point), axis=1)
    allowed = np.maximum(radii, 10) + 5
    candidates = np.flatnonzero(distance <= allowed)
    return int(candidates[np.argmin(distance[candidates])]) if len(candidates) else None


def display_radii(bodies, span, height, physical=False):
    if physical:
        return np.array([b.radius * height / span for b in bodies])
    sizes = np.array([13, 4, 6, 6.5, 5, 11, 10, 8, 8], dtype=float)
    zoom = np.clip((5 * AU / span) ** .13, .75, 2.4)
    return np.maximum(sizes[:len(bodies)] * zoom,
                      np.array([b.radius * height / span for b in bodies]))
