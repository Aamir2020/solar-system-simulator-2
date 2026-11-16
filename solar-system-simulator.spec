# Build on the target OS: pyinstaller --noconfirm solar-system-simulator.spec
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH)
package = root / 'src' / 'solar_system_simulator'
data = [(str(package / 'assets' / name), 'solar_system_simulator/assets')
         for name in ('nasa-logo.svg', 'ATTRIBUTION.md', 'app-icon.png', 'app-icon.ico', 'app-icon.icns', 'app-icon.json')]
data += [(str(asset), 'solar_system_simulator/assets/textures')
         for asset in (package / 'assets' / 'textures').iterdir() if asset.is_file()]
data += [(str(shader), 'solar_system_simulator/rendering')
         for shader in (package / 'rendering').glob('*.glsl')]
a = Analysis(
    [str(root / 'launch.py')],
    pathex=[str(root / 'src')],
    binaries=[], datas=data, hiddenimports=['moderngl'] + collect_submodules('glcontext'),
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['matplotlib'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Solar System Simulator',
          debug=False, strip=False, upx=False, console=False,
          icon=str(package / 'assets' / ('app-icon.icns' if sys.platform == 'darwin' else 'app-icon.ico'))
               if sys.platform in ('win32', 'darwin') else None)
if sys.platform == 'darwin':
    app = BUNDLE(exe, name='Solar System Simulator.app',
                 icon=str(package / 'assets' / 'app-icon.icns'),
                 bundle_identifier='com.aamir2020.solarsystemsimulator')
