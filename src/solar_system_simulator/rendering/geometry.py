"""Indexed sphere and annulus meshes with equirectangular surface coordinates."""
import numpy as np


def sphere_mesh(longitudes=128, latitudes=64):
    u, v = np.meshgrid(np.linspace(0, 1, longitudes + 1), np.linspace(0, 1, latitudes + 1))
    longitude, latitude = 2*np.pi*(u - .5), np.pi*v
    points = np.stack((np.sin(latitude)*np.cos(longitude),
                       np.sin(latitude)*np.sin(longitude), np.cos(latitude)), axis=-1)
    vertices = np.concatenate((points, u[..., None], v[..., None]), axis=-1).reshape(-1, 5)
    a = (np.arange(latitudes)[:, None]*(longitudes + 1) + np.arange(longitudes)).ravel()
    b = a + longitudes + 1
    indices = np.column_stack((a, b, a+1, a+1, b, b+1)).ravel()
    return vertices.astype('f4'), indices.astype('u4')


def ring_mesh(segments=256, inner=1.24, outer=2.32):
    vertices = []
    for angle in np.linspace(0, 2*np.pi, segments + 1):
        for radius, u in ((inner, 0.), (outer, 1.)):
            vertices.append([radius*np.cos(angle), radius*np.sin(angle), 0., u, .5])
    a = np.arange(segments)*2
    indices = np.column_stack((a, a+1, a+2, a+2, a+1, a+3)).ravel()
    return np.array(vertices, dtype='f4'), indices.astype('u4')


def axial_rotation(index):
    # Illustrative fixed axes, not NASA attitude/rotation ephemerides.
    tilts = [7.25, .03, 177.4, 23.4, 25.2, 3.1, 26.7, 97.8, 28.3]
    tilt = np.radians(tilts[index])
    return np.array([[1, 0, 0], [0, np.cos(tilt), np.sin(tilt)],
                     [0, -np.sin(tilt), np.cos(tilt)]])
