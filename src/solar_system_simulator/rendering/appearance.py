"""Approximate visible-light point colors, separate from the UI/trail palette.

These sRGB choices illustrate observed hues; they are not measured photometry.
Sun: https://soho.nascom.nasa.gov/classroom/faq.html
Earth: https://www.jpl.nasa.gov/news/pale-blue-dot-revisited/
Ice giants: https://doi.org/10.1093/mnras/stad3761
Other planets: https://www.nasa.gov/centers-and-facilities/goddard/using-planet-colors-to-search-for-alien-earths/
Saturn: https://www.jpl.nasa.gov/news/press_kits/cassini-arrival.pdf
Point sizes retain visibility and solar dominance rather than model exposure.
"""
import numpy as np

from ..data.catalog import AU, BODIES

POINT_COLORS = ('#ffffff', '#e5ded4', '#fff6e5', '#b8d9ff', '#f0ad83',
                '#f4e9cf', '#eee0b9', '#bcdcd6', '#b4d4d7')
POINT_RADII = np.array([3., .85, 1.3, 1.05, 1., 1.2, 1., .8, .8])
# V-band geometric albedos from JPL Solar System Dynamics. The Sun emits rather
# than reflects visible light, so its entry is deliberately not used.
GEOMETRIC_ALBEDOS = np.array([0., .106, .65, .367, .15, .52, .47, .51, .41])
TEXTURE_FADE_START = 6.
TEXTURE_FADE_END = 16.
MINIMUM_POINT_BRIGHTNESS = .08
MAXIMUM_PLANET_BRIGHTNESS = .85


def apparent_radii(physical_radii, depths, focal, physical=False):
    """Enlarged discs shrink with observer distance until their light is unresolved."""
    radii = physical_radii.copy()
    if not physical:
        reference_distance = 5*AU / (2*np.tan(np.pi/8))
        sizes = np.array([18., 4., 6., 6.5, 5., 11., 10., 8., 8.])
        pixels = sizes*np.minimum(np.sqrt(reference_distance/np.maximum(depths, 1.)), 2.4)
        radii = np.maximum(radii, pixels*np.maximum(depths, 0)/focal)
    return radii


def point_weights(physical_pixels):
    """Fade unresolved lights only when the physical surface becomes discernible."""
    resolved = np.clip((physical_pixels-TEXTURE_FADE_START) /
                       (TEXTURE_FADE_END-TEXTURE_FADE_START), 0, 1)
    resolved = resolved**2*(3-2*resolved)
    return 1-resolved


def lambert_phase(angle):
    """Disk-integrated reflected-light fraction for a diffuse sphere."""
    angle = np.clip(angle, 0, np.pi)
    return (np.sin(angle)+(np.pi-angle)*np.cos(angle))/np.pi


def reflected_fluxes(positions, observer):
    """Planet flux relative to a full Earth, with both distances equal to one AU."""
    positions = np.asarray(positions, dtype=float)
    observer = np.asarray(observer, dtype=float)
    planets = positions[1:]
    to_sun = positions[0]-planets
    to_observer = observer-planets
    sun_distances = np.maximum(np.linalg.norm(to_sun, axis=1), 1.)
    observer_distances = np.maximum(np.linalg.norm(to_observer, axis=1), 1.)
    cosine = np.einsum('ij,ij->i', to_sun, to_observer)/(sun_distances*observer_distances)
    phase = lambert_phase(np.arccos(np.clip(cosine, -1, 1)))
    radii = np.array([body.radius for body in BODIES[1:]])
    earth_radius = BODIES[3].radius
    earth_albedo = GEOMETRIC_ALBEDOS[3]
    return (GEOMETRIC_ALBEDOS[1:]/earth_albedo * (radii/earth_radius)**2 *
            (AU/sun_distances)**2 * (AU/observer_distances)**2 * phase)


def point_brightness(positions, observer):
    """Compress physical flux for display while keeping every selectable body visible."""
    levels = np.ones(len(BODIES))
    levels[1:] = np.clip(reflected_fluxes(positions, observer)**.25,
                         MINIMUM_POINT_BRIGHTNESS, MAXIMUM_PLANET_BRIGHTNESS)
    return levels
