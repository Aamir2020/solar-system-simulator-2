"""Re-download the attributed, unmodified Solar System Scope 2K planet maps.

Run with the project's environment from any directory. Downloads are validated with
Qt before replacing existing assets. Runtime never needs to download these files.
"""
from hashlib import sha256
import json
from pathlib import Path

from PySide6.QtGui import QImage
import requests

MAPS = {
    'Sun': '2k_sun.jpg',
    'Mercury': '2k_mercury.jpg',
    'Venus': '2k_venus_atmosphere.jpg',
    'Earth': '2k_earth_daymap.jpg',
    'Mars': '2k_mars.jpg',
    'Jupiter': '2k_jupiter.jpg',
    'Saturn': '2k_saturn.jpg',
    'Uranus': '2k_uranus.jpg',
    'Neptune': '2k_neptune.jpg',
}
BASE = 'https://www.solarsystemscope.com/textures/download/'


def main():
    directory = Path(__file__).resolve().parents[1] / 'src/solar_system_simulator/assets/textures'
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {}
    with requests.Session() as session:
        for body, filename in MAPS.items():
            response = session.get(BASE + filename, timeout=(10, 45))
            response.raise_for_status()
            data = response.content
            image = QImage.fromData(data)
            if image.isNull() or image.width() != 2048 or image.height() != 1024:
                raise ValueError(f'{body}: expected a 2048×1024 equirectangular image')
            (directory / filename).write_bytes(data)
            manifest[body] = {'file': filename, 'url': BASE + filename,
                              'sha256': sha256(data).hexdigest(),
                              'width': image.width(), 'height': image.height()}
            print(f'{body}: {len(data):,} bytes', flush=True)
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
