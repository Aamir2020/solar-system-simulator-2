"""Projection, apparent body sizes, occlusion, and clipped orbit ribbons."""
import math
from dataclasses import dataclass

import numpy as np

from ..data.catalog import AU, BODIES


@dataclass
class BodyLayout:
    points: np.ndarray
    depths: np.ndarray
    world_radii: np.ndarray
    screen_radii: np.ndarray
    visible: np.ndarray


def body_layout(camera, positions, width, height, physical=False):
    points, depths = camera.project(positions, width, height)
    focal = height / (2*math.tan(camera.fov / 2))
    radii = np.array([body.radius for body in BODIES])
    if not physical:
        pixels = np.array([13, 4, 6, 6.5, 5, 11, 10, 8, 8])
        pixels *= np.clip((5*AU/camera.span)**.13, .75, 2.4)
        radii = np.maximum(radii, pixels*np.maximum(depths, 0)/focal)
    projected = focal*radii/np.sqrt(np.maximum(depths**2 - radii**2, 1.))
    projected = np.minimum(projected, 4*max(width, height))
    visible = (depths > radii) & np.isfinite(points).all(axis=1)
    for far in range(len(BODIES)):
        if not visible[far]:
            continue
        for near in range(len(BODIES)):
            if near == far or not visible[near] or depths[near] >= depths[far]:
                continue
            if np.linalg.norm(points[far] - points[near]) + projected[far] < projected[near]:
                visible[far] = False
                break
    return BodyLayout(points, depths, radii, projected, visible)


def trail_history(snapshot, elapsed, positions, limit):
    end = np.searchsorted(snapshot.trail_times, elapsed, side='left')
    start = max(0, end - (limit - 1))
    return np.concatenate((snapshot.trails[start:end], positions[None]))


def pick_sphere(camera, positions, radii, point, width, height):
    origin, direction = camera.ray(point, width, height)
    relative = positions - origin
    along = relative @ direction
    perpendicular = relative - along[:, None]*direction
    discriminant = radii**2 - np.sum(perpendicular**2, axis=1)
    distance = along - np.sqrt(np.maximum(discriminant, 0))
    hits = (discriminant >= 0) & (distance > 0)
    if not hits.any():
        return None
    return int(np.argmin(np.where(hits, distance, np.inf)))


def trail_vertices(camera, history, width, height):
    """Clip segments at the eye plane before expanding them into pixel-width ribbons."""
    if len(history) < 2:
        return np.empty((0, 6), dtype='f4')
    view = camera.to_view(history) / camera.distance
    ages = np.linspace(.03, 1, len(view))
    a, b = view[:-1].copy(), view[1:].copy()
    age_a, age_b = ages[:-1].copy(), ages[1:].copy()
    near = 1e-5
    valid = (a[:, 2] >= near) | (b[:, 2] >= near)
    a, b, age_a, age_b = a[valid], b[valid], age_a[valid], age_b[valid]
    for first, second, first_age, second_age in ((a, b, age_a, age_b), (b, a, age_b, age_a)):
        behind = first[:, 2] < near
        t = (near - first[behind, 2])/(second[behind, 2] - first[behind, 2])
        first[behind] += (second[behind] - first[behind])*t[:, None]
        first_age[behind] += (second_age[behind] - first_age[behind])*t
    focal = height/(2*math.tan(camera.fov/2))
    screen_a = a[:, :2]/a[:, 2:]*[focal, -focal] + [width/2, height/2]
    screen_b = b[:, :2]/b[:, 2:]*[focal, -focal] + [width/2, height/2]
    margin = 4.
    keep = ((np.minimum(screen_a[:, 0], screen_b[:, 0]) < width+margin) &
            (np.maximum(screen_a[:, 0], screen_b[:, 0]) > -margin) &
            (np.minimum(screen_a[:, 1], screen_b[:, 1]) < height+margin) &
            (np.maximum(screen_a[:, 1], screen_b[:, 1]) > -margin))
    a, b, age_a, age_b = a[keep], b[keep], age_a[keep], age_b[keep]
    direction = screen_b[keep] - screen_a[keep]
    normal = np.column_stack((-direction[:, 1], direction[:, 0]))
    normal /= np.maximum(np.linalg.norm(direction, axis=1)[:, None], 1e-8)
    normal *= 1.4
    vertices = np.empty((len(a), 6, 6), dtype='f4')
    vertices[:, :, :3] = np.stack((a, a, b, b, a, b), axis=1)
    vertices[:, :, 3:5] = np.stack((-normal, normal, -normal, -normal, normal, normal), axis=1)
    vertices[:, :, 5] = np.stack((age_a, age_a, age_b, age_b, age_a, age_b), axis=1)
    return vertices.reshape(-1, 6)
