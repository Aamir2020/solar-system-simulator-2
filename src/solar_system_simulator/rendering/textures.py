"""Decode bundled image maps and create mipmapped, image-backed OpenGL textures."""
import json
from importlib.resources import files

from ..data.catalog import BODIES


def texture_manifest():
    directory = files('solar_system_simulator').joinpath('assets/textures')
    return json.loads(directory.joinpath('manifest.json').read_text())


def image_data(body_name, max_size=None):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage
    directory = files('solar_system_simulator').joinpath('assets/textures')
    entry = texture_manifest()[body_name]
    data = directory.joinpath(entry['file']).read_bytes()
    image = QImage.fromData(data)
    if image.isNull():
        raise ValueError(f'Unable to decode the {body_name} image map.')
    if max_size and max(image.width(), image.height()) > max_size:
        image = image.scaled(max_size, max_size, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    return (image.width(), image.height()), bytes(image.constBits())


def load_texture(context, name, max_size=None):
    import moderngl
    limit = min(max_size or 8192, context.info['GL_MAX_TEXTURE_SIZE'])
    size, pixels = image_data(name, max_size=limit)
    texture = context.texture(size, 4, pixels, alignment=1)
    try:
        texture.repeat_x = name != 'Saturn rings'
        texture.repeat_y = False
        texture.build_mipmaps()
        texture.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        return texture
    except Exception:
        texture.release()
        raise


def load_body_textures(context):
    textures = []
    try:
        for body in BODIES:
            textures.append(load_texture(context, body.name))
    except Exception:
        for texture in textures:
            texture.release()
        raise
    return textures
