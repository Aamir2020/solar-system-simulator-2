# Build on the target OS: pyinstaller --noconfirm orbital.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH)
package = root / 'src' / 'solar_system_simulator'
data = [(str(package / 'assets' / 'demo.json'), 'solar_system_simulator/assets')]
data += [(str(package / 'assets' / name), 'solar_system_simulator/assets')
         for name in ('nasa-logo.svg', 'ATTRIBUTION.md')]
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
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Orbital',
          debug=False, strip=False, upx=False, console=False)
