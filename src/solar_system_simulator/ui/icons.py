"""Small, image-mapped globes for the body explorer, independent of OpenGL."""
from importlib.resources import files

import numpy as np
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap

from ..rendering.textures import image_data


def _saturn_ring_layers(x, y):
    """Project the real ring map into a tilted ellipse, split at the planet's depth."""
    angle = np.radians(25)
    major = x*np.cos(angle) + y*np.sin(angle)
    minor = -x*np.sin(angle) + y*np.cos(angle)
    radius = np.sqrt(major**2 + (minor/.45)**2)
    (width, height), data = image_data('Saturn rings')
    texture = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 4)
    radial_u = np.clip((radius-1.24)/(2.32-1.24), 0, 1)
    rings = texture[height//2, (radial_u*(width-1)).astype(int)].copy()
    rings[:, :, :3] = np.clip(rings[:, :, :3].astype(float)*1.25, 0, 255).astype(np.uint8)
    rings[:, :, 3] *= (radius >= 1.24) & (radius <= 2.32)
    back, front = rings.copy(), rings.copy()
    back[:, :, 3] *= minor >= 0
    front[:, :, 3] *= minor < 0
    return back, front


def _rgba_image(pixels):
    height, width, _ = pixels.shape
    return QImage(pixels.data, width, height, width*4, QImage.Format.Format_RGBA8888).copy()


def body_icon(body):
    # Render at 3x resolution so the same icon stays crisp on high-DPI screens.
    size = 96
    # Fit Saturn's complete ring silhouette inside the same logical icon size.
    radius = (size/2 - 5) / (2.32 if body.name == 'Saturn' else 1.)
    axis = (np.arange(size) + .5 - size/2) / radius
    x, y = np.meshgrid(axis, -axis)
    squared = x*x + y*y
    z = np.sqrt(np.maximum(0., 1-squared))
    width_height, pixels = image_data(body.name)
    width, height = width_height
    texture = np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 4)
    u = np.clip((.5 + np.arctan2(x, z)/(2*np.pi)) * (width-1), 0, width-1).astype(int)
    v = np.clip((.5 - np.arcsin(np.clip(y, -1, 1))/np.pi) * (height-1), 0, height-1).astype(int)
    globe = texture[v, u].copy()
    if body.name != 'Sun':
        light = np.clip(-.3*x + .4*y + .85*z, 0, 1)
        globe[:, :, :3] = (globe[:, :, :3] * (.3 + .7*light[:, :, None])).astype(np.uint8)
    globe[:, :, 3] = np.clip((1-np.sqrt(squared)) * size/2, 0, 1) * 255
    image = _rgba_image(globe)
    if body.name == 'Saturn':
        back, front = _saturn_ring_layers(x, y)
        image = QImage(size, size, QImage.Format.Format_RGBA8888)
        image.fill(0)
        painter = QPainter(image)
        try:
            painter.drawImage(0, 0, _rgba_image(back))
            painter.drawImage(0, 0, _rgba_image(globe))
            painter.drawImage(0, 0, _rgba_image(front))
        finally:
            painter.end()
    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(3)
    return QIcon(pixmap)


def application_icon():
    pixmap = QPixmap()
    if not pixmap.loadFromData(files('solar_system_simulator').joinpath('assets/app-icon.png').read_bytes()):
        raise ValueError('Unable to load the application icon.')
    return QIcon(pixmap)
