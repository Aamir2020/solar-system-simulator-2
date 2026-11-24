"""Meshes and deterministic body orientation from elapsed simulation time."""
import numpy as np

from ..data.catalog import DAY

# The Sun uses NASA's adopted period at 16 degrees latitude. Planet values are
# signed JPL sidereal periods; retrograde direction is represented by the two
# rotation axes whose obliquity exceeds 90 degrees.
# https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html
# https://ssd.jpl.nasa.gov/planets/phys_par.html
SIDEREAL_ROTATION_DAYS = np.array([
    25.38, 58.6462, -243.018, .99726968, 1.02595676,
    .41354, .44401, -.71833, .67125,
])
AXIAL_TILTS_DEGREES = np.array([7.25, .03, 177.4, 23.4, 25.2, 3.1, 26.7, 97.8, 28.3])
# A small illustrative eastward drift separates the static cloud map from the
# surface. Weather is not modeled; this only avoids clouds being painted to land.
EARTH_CLOUD_ROTATION_DAYS = abs(SIDEREAL_ROTATION_DAYS[3]) * .96


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


def axial_rotation(index, elapsed=0.):
    """Return illustrative axis tilt plus physical sidereal spin at ``elapsed``."""
    tilt = np.radians(AXIAL_TILTS_DEGREES[index])
    period = abs(SIDEREAL_ROTATION_DAYS[index]) * DAY
    angle = np.remainder(2*np.pi*elapsed/period, 2*np.pi)
    ct, st = np.cos(tilt), np.sin(tilt)
    ca, sa = np.cos(angle), np.sin(angle)
    tilt_rotation = np.array([[1, 0, 0], [0, ct, st], [0, -st, ct]])
    spin_rotation = np.array([[ca, -sa, 0], [sa, ca, 0], [0, 0, 1]])
    return tilt_rotation @ spin_rotation


def earth_cloud_offset(elapsed):
    """Return cloud-map revolutions ahead of Earth's surface, wrapped for precision."""
    surface_period = abs(SIDEREAL_ROTATION_DAYS[3]) * DAY
    cloud_period = EARTH_CLOUD_ROTATION_DAYS * DAY
    return float(np.remainder(elapsed/cloud_period - elapsed/surface_period, 1.))
