"""Projection, apparent body sizes, occlusion, and clipped orbit ribbons."""
import math
from dataclasses import dataclass

import numpy as np

from ..data.catalog import BODIES
from .appearance import POINT_RADII, apparent_radii, point_weights


@dataclass
class BodyLayout:
    points: np.ndarray
    depths: np.ndarray
    world_radii: np.ndarray
    screen_radii: np.ndarray
    visible: np.ndarray
    disc_radii: np.ndarray
    point_weights: np.ndarray
    light_radii: np.ndarray


def body_layout(camera, positions, width, height, physical=False):
    points, depths = camera.project(positions, width, height)
    focal = height / (2*math.tan(camera.fov / 2))
    physical_radii = np.array([body.radius for body in BODIES])
    physical_projected = focal*physical_radii/np.sqrt(
        np.maximum(depths**2-physical_radii**2, 1.))
    radii = apparent_radii(physical_radii, depths, focal, physical)
    projected = focal*radii/np.sqrt(np.maximum(depths**2 - radii**2, 1.))
    projected = np.minimum(projected, 4*max(width, height))
    weights = point_weights(physical_projected)
    light_radii = np.maximum(POINT_RADII, projected*.8)
    screen_radii = np.maximum(projected*(1-weights), light_radii*weights)
    visible = (depths > radii) & np.isfinite(points).all(axis=1)
    for far in range(len(BODIES)):
        if not visible[far]:
            continue
        for near in range(len(BODIES)):
            if near == far or not visible[near] or depths[near] >= depths[far]:
                continue
            if np.linalg.norm(points[far] - points[near]) + screen_radii[far] < screen_radii[near]:
                visible[far] = False
                break
    return BodyLayout(points, depths, radii, screen_radii, visible,
                      projected, weights, light_radii)


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


def orbit_trail(history, centers):
    """Keep the newest revolution about the moving Sun, avoiding stacked old laps."""
    if len(history) < 3:
        return history
    relative = history - centers
    angles = np.arctan2(np.linalg.norm(np.cross(relative[:-1], relative[1:]), axis=1),
                        np.einsum('ij,ij->i', relative[:-1], relative[1:]))
    backward = np.concatenate(([0.], np.cumsum(angles[::-1])))
    boundary = int(np.searchsorted(backward, 2*math.pi))
    if boundary >= len(history):
        return history
    start = len(history) - 1 - boundary
    fraction = (backward[boundary] - 2*math.pi)/angles[start]
    tail = history[start] + fraction*(history[start+1] - history[start])
    return np.concatenate((tail[None], history[start+1:]))


def trail_vertices(camera, history, width, height):
    """Build a joined, tapered ribbon, retaining continuous joins across viewport clipping."""
    if len(history) < 2:
        return np.empty((0, 6), dtype='f4')
    view = camera.to_view(history) / camera.distance
    lengths = np.linalg.norm(np.diff(view, axis=0), axis=1)
    view = view[np.concatenate(([True], lengths > 0))]
    lengths = lengths[lengths > 0]
    if not lengths.sum():
        return np.empty((0, 6), dtype='f4')
    ages = np.concatenate(([0.], np.cumsum(lengths)))/lengths.sum()
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
    direction = screen_b - screen_a
    length = np.linalg.norm(direction, axis=1)
    normal = np.column_stack((-direction[:, 1], direction[:, 0]))
    normal /= np.maximum(length[:, None], 1e-8)
    start_normal, end_normal = normal.copy(), normal.copy()
    # Neighbouring quads share precisely the same edge at a turn. Independent
    # perpendicular offsets leave wedges which blend twice (or expose gaps).
    joined = np.all(b[:-1] == a[1:], axis=1) & (length[:-1] > 1e-8) & (length[1:] > 1e-8)
    miter = normal[:-1] + normal[1:]
    miter /= np.maximum(np.linalg.norm(miter, axis=1)[:, None], 1e-8)
    miter /= np.maximum(np.einsum('ij,ij->i', miter, normal[1:])[:, None], .35)
    end_normal[:-1][joined] = miter[joined]
    start_normal[1:][joined] = miter[joined]
    start_normal *= (.35 + 1.25*age_a)[:, None]
    end_normal *= (.35 + 1.25*age_b)[:, None]
    margin = 5.
    keep = ((np.minimum(screen_a[:, 0], screen_b[:, 0]) < width+margin) &
            (np.maximum(screen_a[:, 0], screen_b[:, 0]) > -margin) &
            (np.minimum(screen_a[:, 1], screen_b[:, 1]) < height+margin) &
            (np.maximum(screen_a[:, 1], screen_b[:, 1]) > -margin))
    keep &= length > 1e-8
    a, b, age_a, age_b = a[keep], b[keep], age_a[keep], age_b[keep]
    start_normal, end_normal = start_normal[keep], end_normal[keep]
    vertices = np.empty((len(a), 6, 6), dtype='f4')
    vertices[:, :, :3] = np.stack((a, a, b, b, a, b), axis=1)
    vertices[:, :, 3:5] = np.stack((-start_normal, start_normal, -end_normal,
                                   -end_normal, start_normal, end_normal), axis=1)
    vertices[:, :, 5] = np.stack((age_a, age_a, age_b, age_b, age_a, age_b), axis=1)
    return vertices.reshape(-1, 6)
