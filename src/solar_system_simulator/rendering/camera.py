"""Double-precision orbit camera; world coordinates stay out of GPU float buffers."""
import math

import numpy as np

from ..data.catalog import AU


def world_vector(value):
    value = np.asarray(value, dtype=np.float64)
    if value.shape[-1] == 2:
        value = np.pad(value, [(0, 0)] * (value.ndim - 1) + [(0, 1)])
    return value


class Camera:
    def __init__(self):
        self.center = np.zeros(3, dtype=np.float64)
        self.span = 5 * AU
        self.target_center = self.center.copy()
        self.target_span = self.span
        self.minimum_span = .00005 * AU
        self.fov = math.radians(45)
        self.yaw = 0.
        self.pitch = math.radians(55)
        self._zoom_anchor = None
        self._zoom_offset = np.zeros(3, dtype=np.float64)

    @property
    def distance(self):
        return self.span / (2 * math.tan(self.fov / 2))

    @property
    def basis(self):
        sy, cy = math.sin(self.yaw), math.cos(self.yaw)
        sp, cp = math.sin(self.pitch), math.cos(self.pitch)
        right = np.array([cy, sy, 0.])
        back = np.array([sy * cp, -cy * cp, sp])
        return right, np.cross(back, right), back

    @property
    def eye(self):
        return self.center + self.basis[2] * self.distance

    @property
    def view_rotation(self):
        right, up, back = self.basis
        return np.array([right, up, -back])

    def to_view(self, positions):
        view = (world_vector(positions) - self.center) @ self.view_rotation.T
        view[..., 2] += self.distance
        return view

    def project(self, positions, width, height):
        view = self.to_view(positions)
        depth = view[..., 2]
        safe = np.where(depth > self.distance * 1e-8, depth, np.nan)
        focal = height / (2 * math.tan(self.fov / 2))
        screen = view[..., :2] * [focal, -focal] / safe[..., None] + [width / 2, height / 2]
        return screen, depth

    def to_screen(self, positions, width, height):
        return self.project(positions, width, height)[0]

    def to_world(self, point, width, height):
        right, up, _ = self.basis
        x, y = np.asarray(point) - [width / 2, height / 2]
        return self.center + (right * x - up * y) * self.span / height

    def ray(self, point, width, height):
        right, up, back = self.basis
        x, y = (np.asarray(point) - [width / 2, height / 2]) / height
        direction = -back + 2 * math.tan(self.fov / 2) * (right * x - up * y)
        return self.eye, direction / np.linalg.norm(direction)

    def zoom(self, point, factor, width, height, *, following=False):
        if (factor - 1) * (self.target_span - self.span) < 0:
            self.target_span = self.span
        self.target_span = float(np.clip(self.target_span * factor, self.minimum_span, 2000 * AU))
        if following:
            self._zoom_anchor = None
        else:
            self._zoom_anchor = self.to_world(point, width, height)
            self._zoom_offset = (self._zoom_anchor - self.center) / self.span
            self.target_center = self._zoom_anchor - self._zoom_offset * self.target_span

    def orbit(self, dx, dy):
        self._zoom_anchor = None
        self.yaw = (self.yaw - dx * .006) % (2 * math.pi)
        self.pitch = float(np.clip(self.pitch + dy * .006, -math.pi / 2, math.pi / 2))

    def top_down(self):
        self._zoom_anchor = None
        self.yaw, self.pitch = 0., math.pi / 2

    def perspective(self):
        self._zoom_anchor = None
        self.yaw, self.pitch = 0., math.radians(55)

    def pan(self, dx, dy, height):
        self._zoom_anchor = None
        right, up, _ = self.basis
        self.center += (-right * dx + up * dy) * self.span / max(height, 1)
        self.target_center = self.center.copy()

    def preset(self, center, span):
        self._zoom_anchor = None
        self.target_center = world_vector(center).copy()
        self.target_span = float(np.clip(span, self.minimum_span, 2000 * AU))

    def keep_outside(self, positions, radii):
        """Keep free-camera zoom/pan outside physical surfaces without moving the simulation."""
        offset = self.eye - positions
        distances = np.linalg.norm(offset, axis=1)
        index = int(np.argmin(distances/radii))
        clearance = radii[index]*1.05
        if distances[index] >= clearance:
            return
        direction = offset[index]/distances[index] if distances[index] > 0 else self.basis[2]
        push = direction*(clearance-distances[index])
        self.center += push
        self.target_center += push
        self._zoom_anchor = None

    def animate(self, dt, follow=None):
        dt = max(0., min(dt, .1))
        self.target_span = max(self.target_span, self.minimum_span)
        alpha = 1 - math.exp(-dt * 18)
        self.span = math.exp(math.log(self.span) +
                             (math.log(self.target_span) - math.log(self.span)) * alpha)
        if abs(self.span / self.target_span - 1) < 1e-6:
            self.span = self.target_span
        if follow is not None:
            self.center = world_vector(follow).copy()
            self.target_center = self.center.copy()
            self._zoom_anchor = None
        elif self._zoom_anchor is not None:
            self.center = self._zoom_anchor - self._zoom_offset * self.span
            if self.span == self.target_span:
                self.target_center = self.center.copy()
                self._zoom_anchor = None
        else:
            self.center += (self.target_center - self.center) * (1 - math.exp(-dt * 10))


def pick_body(screen_positions, radii, point, depths=None, visible=None):
    distance = np.linalg.norm(screen_positions - np.asarray(point), axis=1)
    mask = distance <= np.maximum(radii, 10) + 5
    if visible is not None:
        mask &= visible
    candidates = np.flatnonzero(mask)
    if not len(candidates):
        return None
    if depths is not None:
        return int(candidates[np.argmin(np.asarray(depths)[candidates])])
    return int(candidates[np.argmin(distance[candidates])])


def display_radii(bodies, span, height, physical=False):
    physical_radii = np.array([b.radius * height / span for b in bodies])
    if physical:
        return physical_radii
    sizes = np.array([13, 4, 6, 6.5, 5, 11, 10, 8, 8], dtype=float)
    zoom = np.clip((5 * AU / span) ** .13, .75, 2.4)
    return np.maximum(sizes[:len(bodies)] * zoom, physical_radii)
