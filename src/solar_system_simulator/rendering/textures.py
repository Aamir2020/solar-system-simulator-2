"""Decode bundled image maps and create mipmapped, image-backed OpenGL textures."""
import json
from importlib.resources import files

from ..data.catalog import BODIES


def texture_manifest():
    directory = files('solar_system_simulator').joinpath('assets/textures')
    return json.loads(directory.joinpath('manifest.json').read_text())


def image_data(body_name):
    from PySide6.QtGui import QImage
    directory = files('solar_system_simulator').joinpath('assets/textures')
    entry = texture_manifest()[body_name]
    data = directory.joinpath(entry['file']).read_bytes()
    image = QImage.fromData(data).convertToFormat(QImage.Format.Format_RGBA8888)
    if image.isNull():
        raise ValueError(f'Unable to decode the {body_name} image map.')
    return (image.width(), image.height()), bytes(image.constBits())


def load_body_textures(context):
    import moderngl
    textures = []
    try:
        for body in BODIES:
            size, pixels = image_data(body.name)
            texture = context.texture(size, 4, pixels, alignment=1)
            textures.append(texture)
            texture.repeat_x = True
            texture.repeat_y = False
            texture.build_mipmaps()
            texture.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
    except Exception:
        for texture in textures:
            texture.release()
        raise
    return textures
