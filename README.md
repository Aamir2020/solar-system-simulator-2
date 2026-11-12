# Orbital · Solar System Simulator 2

A Python desktop solar-system explorer replacing the original Matplotlib display with a PySide6 interface and a ModernGL viewport. It preserves pairwise Newtonian N-body gravity, NumPy float64 state, kick–drift–kick leapfrog integration, and NASA/JPL Horizons initial conditions.

## Run

Requires Python 3.10+ and an OpenGL 3.3 desktop graphics context. The application starts paused with a clearly labeled **synthetic circular-orbit demo**, so first launch does not depend on the network. Select an initial **TDB** date and press **Load NASA** for real Horizons starting vectors, then press **Play**.

Python 3.10/3.11 use PySide6 below 6.12 automatically. The Qt 6.12.0 wheels have an upstream reference-counting regression on these Python versions that can cause `none_dealloc` or `bool_dealloc` fatal crashes during routine GUI updates ([PYSIDE-3474](https://qt-project.atlassian.net/browse/PYSIDE-3474)). If an older installation crashes this way, reactivate its environment and rerun `python -m pip install -e .` to resolve compatible bindings. The application checks this compatibility before importing Qt.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
solar-system
```

On Windows use `.venv\Scripts\activate`. Alternatively run `python -m solar_system_simulator` after installation. A normal desktop session is required; Qt's `offscreen` platform does not support QOpenGLWidget. On Linux, distribution packages for OpenGL/EGL and Qt's xcb or Wayland platform may be needed. An initialization failure is shown in the viewport when Qt can create the window.

To exercise the scientific core without Qt, install NumPy and run directly from source:

```bash
PYTHONPATH=src python -m solar_system_simulator --headless --steps 365 --dt 86400
```

This prints the initial-data source, simulated duration, integration runtime, energy change, and final coordinates. It does not access NASA or launch a GUI.

## Explore

- Scroll to zoom toward the cursor; drag to pan.
- Click a planet or use the searchable body list to inspect it. Double click to focus and follow.
- Camera presets: inner planets, outer planets, whole system, and selected body.
- Inspector: mass, approximate physical radius, barycentric speed and X/Y coordinates, and distance from the Sun.
- Display: image-mapped planetary surfaces, Sun glow, decorative Saturn rings, stable stars, fading historical trails, overlap-aware labels, and physical/exaggerated size modes.
- Transport: pause/play, one numerical step, restart, speed, numerical timestep, and initial date.
- Save a viewport PNG and a matching JSON provenance file. Display settings and window geometry persist locally.

| Shortcut | Action |
| --- | --- |
| Space | Play / pause |
| N | One integration step |
| R | Restart the loaded scenario |
| H | Home camera |
| F | Toggle follow |
| I | Show / hide inspector |
| F11 | Fullscreen |
| Ctrl+S | Screenshot |
| F1 | Controls and scientific limits |
| Ctrl+Q | Quit |

## Scientific model and time

The force law and leapfrog integration preserve the original simulator's method. The initial one-day timestep is the compatibility baseline; six-hour and one-hour steps are available for convergence checks. Increasing playback speed schedules additional fixed steps, without silently increasing the numerical timestep. Batches, trail history, and outgoing snapshots are bounded; the viewport reports achieved speed rather than promising every requested speed can be maintained.

Physics runs on a dedicated worker. Rendering consumes read-only snapshots and interpolates completed states. Display interpolation introduces a small presentation delay; the inspector and date describe the latest authoritative state. Camera-relative GPU coordinates reduce jitter without changing float64 SI physics. Picking and label layout use screen coordinates. When names overlap, both are hidden; the selected name stays visible, or the Sun name if nothing is selected. Names return as zoom separates them. Trails show simulated history, sampled at least one simulated day apart, with up to 1,500 samples, not future orbital predictions. The initial demo has no precomputed history.

This is a **two-dimensional projection**, not a complete ephemeris model. It excludes moons, asteroids, relativity, collisions, and physical rotation. Image maps are visual references; lighting and rings are decorative. Distances stay linear; planet radii are exaggerated by default and marked in the viewport. Physical-size mode can make planets too small to see. The original local mass constants are preserved in `data/catalog.py`; visual radii are approximate metadata.

### NASA Horizons

NASA initializes the state; subsequent motion is integrated locally. Every body uses the same epoch and explicit settings: solar-system barycenter (`500@0`), ICRF, ecliptic J2000, geometric vectors (`VEC_CORR=NONE`), kilometres and kilometres per second, and TDB calendar time. The client converts units to metres and metres per second and keeps X/Y and VX/VY. **The date selector is TDB, not local time or UTC; no implicit timezone conversion occurs.**

Requests are serialized on a background loader, with connection/read timeouts, bounded retries, cancellation, strict vector parsing, epoch validation, and response provenance. Disk cache keys include body, epoch, frame, units, and all request settings. A malformed cache entry is refetched; failed NASA loading retains the current scenario rather than substituting another date. Cancellation can take the current request timeout to finish. Cache storage uses Qt's per-user application cache directory. No account or API key is required.

The bundled offline scenario is generated from approximate circular radii with arbitrary phase angles and barycentric corrections. It is explicitly **not NASA ephemerides**. Selecting another initial date affects only a future NASA load, not the demo's labeled reference epoch (2026-01-01 TDB).

## Development and checks

```bash
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python -m build
```

Tests cover a frozen 30-day output from the unmodified original solver, two-body convergence and conservation, rendering-clock independence, units and NASA cache behavior, cancellation, picking, worker generations, bounded history, and shader compilation/linking. Scientific tests require NumPy and Requests but no GUI. EGL shader tests skip only if a context is unavailable. To run the full desktop smoke test on a graphical session:

```bash
ORBITAL_DESKTOP_TESTS=1 python -m unittest discover -s tests -v
```

On a Linux CI host with Mesa, Qt dependencies, and Xvfb installed, use `xvfb-run -a`. The included GitHub Actions workflow installs those dependencies, runs the suite including the desktop smoke test, and builds the Python distribution. No normal test calls the live NASA service.

Create a native executable after installing the development extras:

```bash
pyinstaller --noconfirm orbital.spec
```

The spec includes shaders, the demo scenario, all planet image maps, and texture attribution. Test the output on the target desktop before distributing it; builds are platform-specific.

### Validation

The Linux/Python 3.10 suite passes all 34 checks, including a real Qt/OpenGL window, 1,000 mouse-move events, singleton reference-count regression checks, image-map decoding/rendering, and zoomed-out label priority (only Sun, or only the selected body). The local environment uses the compatible PySide6 6.11.3 family and passes `pip check`.

Source and wheel distribution builds include all nine image maps, shader files, metadata, and attribution. A 365-step headless integration is also available for checking numerical behavior. Workflow syntax is validated with actionlint. The 60 FPS target is hardware-dependent and has not been benchmarked; the Windows executable itself is built and smoke-tested by the tag-triggered Windows workflow, not on this Linux host.

## Layout

```text
src/solar_system_simulator/
  physics/     # pure NumPy state, leapfrog, and bounded worker
  data/        # body catalog, explicit demo, Horizons client/cache/parser
  rendering/   # camera geometry, Qt/OpenGL viewport, production shaders
  ui/          # main window, controls, theme
  assets/      # reproducible offline reference scenario
```

## Attribution

Original simulator and integration method: Aamir Zekaria Ali, MIT license. The frozen regression fixture records the SHA-256 of the original `orbit_builder.py` and its exact inputs/outputs. Sun and planet image maps are unmodified 2K Solar System Scope / INOVE maps based on NASA imagery, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See [texture attribution](src/solar_system_simulator/assets/textures/ATTRIBUTION.md) for sources, processing notes, and the distinction between these maps and raw spacecraft data. The package and native executable include all maps and attribution, so no texture downloads are needed at runtime. Saturn rings and stars remain rendered decorative effects. Use `python scripts/fetch_textures.py` to reproduce the downloads and provenance manifest. NASA data is fetched on user request through the [JPL Horizons API](https://ssd-api.jpl.nasa.gov/doc/horizons.html); scientific conventions are described in the [Horizons manual](https://ssd.jpl.nasa.gov/horizons/manual.html).

## Automatic Windows releases

Pushing any tag triggers `.github/workflows/release-windows.yml`. It builds a Windows x64 executable using Python 3.11 and PyInstaller, runs tests and a packaged headless smoke check, and publishes these assets to the matching GitHub Release:

- `Orbital-windows-x64.exe` (bundled Python, Qt, shaders, demo, and planet maps)
- `SHA256SUMS`
- `LICENSE.txt` and `TEXTURE-CREDITS.txt`

No separate token is needed: publishing uses the workflow's `GITHUB_TOKEN`, with write access limited to the publishing job. Build artifacts are also retained in Actions for 30 days. A failed build or check prevents publishing. Existing release assets are replaced when rerunning the same tag. Tags containing a hyphen, such as `v2.0.1-rc.1`, create prereleases.

After committing and pushing the desired version, create and push a tag:

```bash
git tag -a v2.0.1 -m "Release v2.0.1"
git push origin v2.0.1
```

The workflow must already exist in that tagged commit. To rebuild an existing tag, choose **Actions → Windows executable release → Run workflow** and enter its tag. The application version in `pyproject.toml` is maintained separately; update it before tagging when changing the package version. Windows binaries are built and tested on GitHub's Windows runner, not cross-compiled locally.
