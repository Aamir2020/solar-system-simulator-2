# Solar System Simulator

Explore the solar system in a Python desktop app. It uses N-body gravity, leapfrog integration, NASA Horizons data, and 3D GPU graphics with textured planets and a Milky Way skybox.

![Demo of the solar system simulator](docs/demo.gif)

*The demo uses initial positions and velocities loaded from NASA Horizons.*

## Install on Windows

1. Open the [latest release](https://github.com/Aamir2020/solar-system-simulator-2/releases/latest).
2. Under **Assets**, download `Solar-System-Simulator-windows-x64.exe`.
3. Open the downloaded file to start the app. You do not need to install Python.

You need 64-bit Windows and a graphics driver with OpenGL 3.3 support.

Choose a date and press **Load NASA**, then press **Play**. The app stays empty until data is loaded. Exact-date NASA responses are cached for later use; there is no bundled sample or synthetic fallback. Dates use **TDB**, the time scale used by the simulation, rather than your local time.

## Run from source

You need Python 3.10+ and a graphics driver with OpenGL 3.3 support.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
solar-system
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

## Controls

- Scroll to zoom. Drag to orbit the camera.
- Shift-drag, middle drag, or right drag to pan.
- Click a planet to select it. Press **Play** to follow it.
- Select another planet while playing to follow that planet.
- Double click a planet to focus on it.
- Use the side panels to change the view, labels, trails, and planet sizes.
- Choose **Enhanced** visibility to keep faint planets discoverable or **Realistic** visibility for physical radii with no minimum brightness.
- Press **Space** to pause, **H** to reset the camera, and **F1** for help.
- Press **T** for the top-down view or **V** for the 3D view.
- Press **Ctrl+S** to save a screenshot.

Planet sizes are enlarged by default. Physics and graphics run in 3D. NASA provides the starting positions and velocities; Python calculates the motion after that. Moons, collisions, and relativity are not included. Body axes are illustrative, while surfaces rotate at their sidereal periods. The skybox is a visual backdrop.

Earth has cloud and night-light maps. Earth, Venus, and Mars have sunlit atmospheric
limbs, and Saturn has textured 3D rings. Adjust sky brightness in the right panel.

Zoom out to see planets shrink into colored points of light. The Sun becomes the largest, brightest white point. See [distant-body colors](docs/appearance.md) for the sources and display choices.

The default physics step is **1 hour**. Larger steps allow faster playback with more orbital error.

## Tests

```bash
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
```

See [physics accuracy](docs/physics-accuracy.md) for the timestep comparison and benchmark command.

## Credits

Code is available under the [MIT license](LICENSE).

Starting data comes from [NASA/JPL Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html). 

Planet maps are by Solar System Scope / INOVE, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). 

See [texture credits](src/solar_system_simulator/assets/textures/ATTRIBUTION.md).
