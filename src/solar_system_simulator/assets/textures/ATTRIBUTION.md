# Planet and sky image maps

Creator: **Solar System Scope / INOVE**.
Source: https://www.solarsystemscope.com/textures/
License: **Creative Commons Attribution 4.0 International (CC BY 4.0)**.
License terms: https://creativecommons.org/licenses/by/4.0/

The nine planet/Sun maps, Earth night and cloud maps, and Saturn's RGBA ring
map are unmodified downloads from the creator's 2K pack. The skybox uses the
unmodified 8K Stars + Milky Way panorama from the same collection.
`manifest.json` records each original URL, dimensions, and SHA-256 digest. The
files are renamed neither for distribution nor rendering. GPU resampling,
spherical projection, and simulated lighting occur at runtime only.

These maps are based on NASA imagery and elevation data, with colors adjusted
by the creator using spacecraft and telescope photographs. The creator notes
that unmapped gaps may use invented terrain and colors are enhanced. They are
visual reference maps, not live NASA data, raw spacecraft products, or measured
planet rotation. Venus uses the atmosphere map rather than its radar surface.
The Sun is emissive; gas giants show atmospheric imagery. Surface maps wrap
actual sphere meshes. Cloud coverage and night lights are static source imagery.
The renderer uses illustrative body axes and initial texture phases. Surface
rotation follows published sidereal periods; Earth's cloud drift is illustrative.
Saturn's ring map wraps a tilted annulus with approximate planetary shadowing.
The sky is direction sampled and oriented for presentation, not a calibrated
star chart. The 8K source is resampled to at most 4K on GPU upload to limit memory.

All texture files remain under CC BY 4.0; the repository's MIT license applies
to application code, not these third-party images. Attribution and the license
link are also accessible in the application's Help dialog.
