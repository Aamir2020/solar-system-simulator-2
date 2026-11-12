"""Diagnose the Qt X11 runtime before a GUI test can abort the Python process."""
import os
from pathlib import Path
import subprocess
import sys


def error(message):
    # Also surface the real loader error in Actions annotations, not just exit code 134.
    escaped = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print(f'::error::{escaped}', flush=True)


def main():
    import PySide6
    from PySide6.QtCore import QLibraryInfo

    print(f'Python {sys.version.split()[0]}, PySide6 {PySide6.__version__}', flush=True)
    plugins = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    libraries = [plugins / 'platforms/libqxcb.so']
    libraries.extend(sorted((plugins / 'xcbglintegrations').glob('*.so')))
    missing = False
    for library in libraries:
        result = subprocess.run(['ldd', str(library)], capture_output=True, text=True, check=False)
        print(f'\n{library.name}\n{result.stdout}', flush=True)
        unresolved = [line.strip() for line in result.stdout.splitlines() if 'not found' in line]
        if result.returncode or unresolved:
            error(f'{library.name}: ' + '; '.join(unresolved or [result.stderr.strip()]))
            missing = True
    if missing:
        return 1

    # Isolate Qt's fatal startup path so its diagnostics survive as workflow annotations.
    probe = subprocess.run(
        [sys.executable, '-c',
         'from PySide6.QtWidgets import QApplication; '
         'app = QApplication([]); print("Qt X11 startup succeeded.", flush=True)'],
        env={**os.environ, 'QT_QPA_PLATFORM': 'xcb', 'QT_DEBUG_PLUGINS': '1'},
        capture_output=True, text=True, timeout=30, check=False,
    )
    print(probe.stdout, end='', flush=True)
    if probe.returncode:
        print(probe.stderr, file=sys.stderr, flush=True)
        error(f'Qt X11 startup failed ({probe.returncode}):\n{probe.stderr[-6000:]}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
