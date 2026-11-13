"""Small, image-mapped globes for the body explorer, independent of OpenGL."""
import numpy as np
from PySide6.QtGui import QIcon, QImage, QPixmap

from ..rendering.textures import image_data


def body_icon(body):
    # Render at 3x resolution so the same icon stays crisp on high-DPI screens.
    size = 96
    axis = (np.arange(size) + .5 - size/2) / (size/2 - 5)
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
    image = QImage(globe.data, size, size, size*4, QImage.Format.Format_RGBA8888).copy()
    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(3)
    return QIcon(pixmap)
