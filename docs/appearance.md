# Distant planets and sunlight

As you move away, textured planets shrink and blend into small points of light.
The Sun becomes a larger, brighter white point. The transition uses the body's
physical angular size, so enlarged display radii cannot reveal a texture from far
away. Zooming close enough to resolve a body restores its textured surface and
Saturn's rings. Points still appear with lighting effects turned off and with
physical planet radii enabled.

The point colors are approximate sRGB display choices, not measured color values:

| Body | Distant appearance |
| --- | --- |
| Sun | White |
| Mercury | Warm gray-white |
| Venus | Cream-white |
| Earth | Pale blue |
| Mars | Orange-red |
| Jupiter | Cream-white |
| Saturn | Pale gold |
| Uranus | Pale greenish blue |
| Neptune | Pale greenish blue, slightly bluer than Uranus |

NASA describes the Sun's visible light as [white](https://soho.nascom.nasa.gov/classroom/faq.html).
[NASA's planet-color overview](https://www.nasa.gov/centers-and-facilities/goddard/using-planet-colors-to-search-for-alien-earths/)
and [Voyager's Pale Blue Dot](https://www.jpl.nasa.gov/news/pale-blue-dot-revisited/)
inform the inner-planet colors. The [Cassini arrival press kit](https://www.jpl.nasa.gov/news/press_kits/cassini-arrival.pdf)
describes Saturn's yellow appearance. [Oxford's reconstructed visible colors](https://www.ox.ac.uk/news/2024-01-05-new-images-reveal-what-neptune-and-uranus-really-look-0)
inform the similar, subdued ice-giant colors.

Point sizes and glow are adjusted for visibility, with the Sun dominant in wide
views. This does not model camera exposure, atmospheric effects, empirical
apparent-magnitude curves, or wavelength-dependent scattering. The physics and
NASA starting data are unchanged.

Planet-point brightness uses each body's radius and [JPL V-band geometric
albedo](https://ssd.jpl.nasa.gov/planets/phys_par.html), inverse-square distance
from the Sun, inverse-square distance from the camera, and a [Lambert phase
function](https://ntrs.nasa.gov/api/citations/20240007032/downloads/Nemati%20Stahl%20HWO%20EB%20Roman%20Lessons%20Final%20SPIE.pdf).
The large physical range is compressed for an ordinary display. A small floor
keeps every planet selectable, and the Sun remains the white exposure reference.

The **Enhanced** visibility mode uses that floor and allows enlarged display
radii. **Realistic** visibility removes the brightness floor and always uses
physical body radii, so a planet can become too faint to see. Both modes use the
same calculated reflected-light brightness and point-to-texture transition.

When effects are enabled, resolved views of Venus, Earth, and Mars add a separate
sunlit atmospheric shell. Its limb is strongest at the horizon and fades toward
the centre and night side. Shell thickness is slightly exaggerated so the thin
edge remains visible at normal screen resolutions; it never changes body size or
simulation state.

Resolved surfaces rotate from elapsed simulation time using [JPL sidereal
periods](https://ssd.jpl.nasa.gov/planets/phys_par.html); Venus and Uranus rotate
retrograde. The Sun uses [NASA's adopted 25.38-day period at 16 degrees
latitude](https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html). Axial
tilts and the initial prime-meridian phase remain illustrative because the image
maps are not attitude ephemerides. Earth's static cloud image drifts slightly
faster than its surface as a visual layer, not as a weather simulation.

Automatic exposure responds to the Sun's apparent size and whether it is inside
the camera view. It smoothly reduces exposure near the Sun and raises it when
looking into dark space. The same exposure is applied to the sky, surfaces,
atmospheres, trails, and unresolved lights with a soft highlight-compression
curve. Exposure compensation is measured in photographic stops (EV), and the
manual mode uses the compensation without automatic solar adjustment. Screenshot
pixels and metadata preserve the exposure visible in the viewport.

Cast shadows compare the apparent discs of the finite-size Sun and every
intervening planet for each rendered fragment. Full overlap creates an umbra;
partial overlap creates a smoothly varying penumbra, matching [NASA's eclipse
geometry](https://science.nasa.gov/eclipses/geometry/). These shadows affect
surfaces, Earth night lights, atmospheres, and Saturn's rings. Saturn's textured
ring opacity also attenuates sunlight reaching the planet. Shadow calculations
are visual only and never modify the N-body state.
