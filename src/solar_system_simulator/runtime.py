"""Check native binding compatibility before importing or constructing Qt objects."""


def desktop_compatibility_error(python_version, pyside_version):
    major, minor = (int(part) for part in pyside_version.split('.')[:2])
    if tuple(python_version[:2]) < (3, 12) and (major, minor) >= (6, 12):
        return (
            f'PySide6 {pyside_version} is incompatible with this application on '
            f'Python {python_version[0]}.{python_version[1]}: Qt 6.12 bindings can corrupt '
            'Python reference counts and abort the process (PYSIDE-3474). '
            'Repair this environment with: python -m pip install -e . '
            '(Python 3.10/3.11 require PySide6 below 6.12).'
        )
    return None
