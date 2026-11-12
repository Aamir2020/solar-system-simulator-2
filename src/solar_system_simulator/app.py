"""Entrypoints. Headless mode exercises science without importing graphics dependencies."""
import argparse
import json
import math
import sys
from time import perf_counter


def main(argv=None):
    parser = argparse.ArgumentParser(description='Orbital · Python N-body solar system simulator')
    parser.add_argument('--headless', action='store_true', help='Integrate the offline demo without a GUI')
    parser.add_argument('--steps', type=int, default=365, help='Headless integration step count')
    parser.add_argument('--dt', type=float, default=86400, help='Headless numerical timestep in seconds')
    args = parser.parse_args(argv)
    if args.steps < 0 or not math.isfinite(args.dt) or args.dt <= 0:
        parser.error('Steps must be nonnegative and dt must be positive.')
    if args.headless:
        from .data.scenario import demo_scenario
        from .physics.system import energy, step
        scenario = demo_scenario()
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
