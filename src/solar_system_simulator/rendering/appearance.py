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
# Slightly exaggerated display shells keep thin atmospheric limbs resolvable.
# Values are body index: (sRGB color, shell radius multiplier, optical strength).
ATMOSPHERES = {
    2: ('#e6c98f', 1.035, .42),
    3: ('#5aafff', 1.030, .58),
    4: ('#d98b62', 1.018, .16),
}
# V-band geometric albedos from JPL Solar System Dynamics. The Sun emits rather
# than reflects visible light, so its entry is deliberately not used.
GEOMETRIC_ALBEDOS = np.array([0., .106, .65, .367, .15, .52, .47, .51, .41])
TEXTURE_FADE_START = 6.
TEXTURE_FADE_END = 16.
MINIMUM_POINT_BRIGHTNESS = .08
MAXIMUM_PLANET_BRIGHTNESS = .85
MINIMUM_EXPOSURE = .04
MAXIMUM_EXPOSURE = 4.


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


def point_brightness(positions, observer, enhanced=True):
    """Tone-map physical flux, optionally retaining a navigation visibility floor."""
    levels = np.ones(len(BODIES))
    minimum = MINIMUM_POINT_BRIGHTNESS if enhanced else 0.
    levels[1:] = np.clip(reflected_fluxes(positions, observer)**.25,
                         minimum, MAXIMUM_PLANET_BRIGHTNESS)
    return levels


def exposure_target(camera, positions, width, height, automatic=True, compensation=0.):
    """Choose camera exposure from visible solar glare, then apply EV compensation."""
    base = 1.
    if automatic:
        base = 1.4
        if positions is not None:
            to_sun = np.asarray(positions[0], dtype=float) - camera.eye
            distance = max(float(np.linalg.norm(to_sun)), BODIES[0].radius*1.000001)
            direction = to_sun/distance
            separation = np.arccos(np.clip(np.dot(-camera.basis[2], direction), -1., 1.))
            half_vertical = camera.fov/2
            half_horizontal = np.arctan(np.tan(half_vertical)*width/max(height, 1))
            half_diagonal = np.arctan(np.hypot(np.tan(half_vertical),
                                               np.tan(half_horizontal)))
            angular_radius = np.arcsin(np.clip(BODIES[0].radius/distance, 0., 1.))
            edge = angular_radius + .12
            visible = np.clip((half_diagonal+edge-separation)/edge, 0., 1.)
            visible = visible**2*(3-2*visible)
            focal = height/(2*np.tan(half_vertical))
            projected = focal*BODIES[0].radius / np.sqrt(max(
                distance**2-BODIES[0].radius**2, 1.))
            glare = (projected/6)**.8
            base /= 1 + visible*glare
    return float(np.clip(base*2**compensation, MINIMUM_EXPOSURE, MAXIMUM_EXPOSURE))


def adapt_exposure(current, target, dt):
    """Smooth exposure in EV space, adapting to brightness faster than darkness."""
    current = float(np.clip(current, MINIMUM_EXPOSURE, MAXIMUM_EXPOSURE))
    target = float(np.clip(target, MINIMUM_EXPOSURE, MAXIMUM_EXPOSURE))
    rate = 5. if target < current else 1.8
    alpha = 1-np.exp(-max(0., min(float(dt), .1))*rate)
    return float(np.exp(np.log(current)*(1-alpha) + np.log(target)*alpha))
