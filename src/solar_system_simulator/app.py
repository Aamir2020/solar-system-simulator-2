"""Entrypoints. Headless mode exercises science without importing graphics dependencies."""
import argparse
import json
import math
import sys
from time import perf_counter


def main(argv=None):
    parser = argparse.ArgumentParser(description='Orbital · Python N-body solar system simulator')
    parser.add_argument('--headless', action='store_true', help='Load NASA data and integrate without a GUI')
    parser.add_argument('--epoch', help='Initial TDB calendar date for headless NASA loading')
    parser.add_argument('--cache-dir', help='Directory for cached NASA responses')
    parser.add_argument('--check-assets', action='store_true', help='Verify bundled graphics without a display or network')
    parser.add_argument('--steps', type=int, default=365, help='Headless integration step count')
    parser.add_argument('--dt', type=float, default=86400, help='Headless numerical timestep in seconds')
    args = parser.parse_args(argv)
    if args.steps < 0 or not math.isfinite(args.dt) or args.dt <= 0:
        parser.error('Steps must be nonnegative and dt must be positive.')
    if args.check_assets:
        from importlib.resources import files
        from .data.catalog import BODIES
        from .rendering.textures import image_data
        try:
            for body in BODIES:
                image_data(body.name)
            root = files('solar_system_simulator')
            if '<svg' not in root.joinpath('assets/nasa-logo.svg').read_text():
                raise ValueError('Invalid NASA logo')
            for name in ('quad', 'body', 'background', 'trail_vertex', 'trail_fragment'):
                if not root.joinpath(f'rendering/{name}.glsl').read_text().startswith('#version'):
                    raise ValueError(f'Invalid shader: {name}')
        except (ImportError, OSError, ValueError, KeyError) as exc:
            print(f'Asset check failed: {exc}', file=sys.stderr)
            return 1
        print('Verified nine planet maps, NASA logo, and five shaders.')
        return 0
    if args.headless:
        if not args.epoch:
            parser.error('--headless requires --epoch, for example --epoch 2026-01-01')
        from pathlib import Path
        from .data.horizons import HorizonsClient, HorizonsError
        from .physics.system import energy, step
        cache = args.cache_dir or Path.home() / '.cache/solar-system-simulator/horizons'
        try:
            scenario = HorizonsClient(cache).load(args.epoch)
        except HorizonsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        state = scenario.state.copy()
        initial = energy(state)
        started = perf_counter()
        for _ in range(args.steps):
            step(state,args.dt)
        runtime = perf_counter()-started
        print(json.dumps({'source':scenario.source,'steps':args.steps,'dt_seconds':args.dt,
            'elapsed_days':state.elapsed/86400,'runtime_seconds':runtime,
            'relative_energy_change':(energy(state)-initial)/abs(initial),
            'positions_m':state.positions.tolist()},indent=2))
        return 0
    try:
        from importlib.metadata import PackageNotFoundError, version
        from .runtime import desktop_compatibility_error
        try:
            pyside_version = version('PySide6')
        except PackageNotFoundError:
            pyside_version = None
        if pyside_version:
            compatibility_error = desktop_compatibility_error(sys.version_info, pyside_version)
            if compatibility_error:
                print(compatibility_error, file=sys.stderr)
                return 1
        from PySide6.QtGui import QSurfaceFormat
        from PySide6.QtWidgets import QApplication
        from .ui.window import MainWindow
    except ImportError as exc:
        print(f'Missing desktop dependency: {exc}. Install with python -m pip install -e .',file=sys.stderr)
        return 1
    fmt = QSurfaceFormat()
    fmt.setVersion(3,3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setSamples(4)
    fmt.setDepthBufferSize(24)
    fmt.setSwapInterval(1)
    QSurfaceFormat.setDefaultFormat(fmt)
    app = QApplication(sys.argv[:1])
    app.setApplicationName('Orbital')
    app.setOrganizationName('Aamir2020')
    window = MainWindow()
    window.show()
    return app.exec()
