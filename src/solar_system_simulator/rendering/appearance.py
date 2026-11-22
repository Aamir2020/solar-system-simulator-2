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

from ..data.catalog import AU

POINT_COLORS = ('#ffffff', '#e5ded4', '#fff6e5', '#b8d9ff', '#f0ad83',
                '#f4e9cf', '#eee0b9', '#bcdcd6', '#b4d4d7')
POINT_RADII = np.array([3., .85, 1.3, 1.05, 1., 1.2, 1., .8, .8])
TEXTURE_FADE_START = 6.
TEXTURE_FADE_END = 16.


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
