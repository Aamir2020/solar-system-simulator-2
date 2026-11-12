from hashlib import sha256
import importlib.util
from importlib.resources import files
import unittest

from solar_system_simulator.data.catalog import BODIES
from solar_system_simulator.rendering.textures import image_data, texture_manifest


class TextureAssetTests(unittest.TestCase):
    def test_every_body_has_its_original_attributed_image(self):
        manifest = texture_manifest()
        self.assertEqual(set(manifest), {body.name for body in BODIES})
        directory = files('solar_system_simulator').joinpath('assets/textures')
        for body in BODIES:
            with self.subTest(body=body.name):
                entry = manifest[body.name]
                data = directory.joinpath(entry['file']).read_bytes()
                self.assertEqual(sha256(data).hexdigest(), entry['sha256'])
                self.assertTrue(data.startswith(b'\xff\xd8'))
                self.assertTrue(entry['url'].startswith('https://www.solarsystemscope.com/'))
        attribution = directory.joinpath('ATTRIBUTION.md').read_text()
        self.assertIn('CC BY 4.0', attribution)
        self.assertIn('Solar System Scope', attribution)

    @unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 is not installed')
    def test_all_images_decode_to_full_resolution_rgba(self):
        for body in BODIES:
            with self.subTest(body=body.name):
                size, data = image_data(body.name)
                self.assertEqual(size, (2048, 1024))
                self.assertEqual(len(data), size[0]*size[1]*4)


@unittest.skipUnless(importlib.util.find_spec('moderngl') and importlib.util.find_spec('PySide6'),
                     'ModernGL and PySide6 are required')
class TextureRenderingTests(unittest.TestCase):
    def test_production_shader_renders_distinct_image_mapped_bodies(self):
        import moderngl
        import numpy as np
        from solar_system_simulator.rendering.textures import load_body_textures
        try:
            context = moderngl.create_context(standalone=True, backend='egl')
        except Exception as exc:
            self.skipTest(f'Headless EGL context unavailable: {exc}')
        resources = []
        try:
            root = files('solar_system_simulator').joinpath('rendering')
            program = context.program(vertex_shader=root.joinpath('quad.glsl').read_text(),
                                      fragment_shader=root.joinpath('body.glsl').read_text())
            resources.append(program)
            quad = np.array([[-1,-1],[1,-1],[-1,1],[-1,1],[1,-1],[1,1]], dtype='f4')
            buffer = context.buffer(quad.tobytes())
            resources.append(buffer)
            vao = context.vertex_array(program, [(buffer, '2f', 'in_pos')])
            resources.append(vao)
            framebuffer = context.simple_framebuffer((128, 128), components=4)
            resources.append(framebuffer)
            framebuffer.use()
            context.viewport = (0,0,128,128)
            program['viewport'].value = (128,128)
            program['center'].value = (64,64)
            program['extent'].value = 128.0
            program['surface_map'].value = 0
            program['effects'].value = False
            program['light_dir'].value = (-.6,.8)
            program['color'].value = (1,1,1)
            textures = load_body_textures(context)
            resources.extend(textures)
            results = []
            for index in (3,4,5):
                program['kind'].value = index
                textures[index].use(location=0)
                framebuffer.clear()
                vao.render()
                pixels = np.frombuffer(framebuffer.read(components=4), dtype=np.uint8).reshape(128,128,4)
                colors = np.unique(pixels[40:88,40:88,:3].reshape(-1,3), axis=0)
                self.assertGreater(len(colors), 100)
                results.append(pixels.copy())
            self.assertFalse(np.array_equal(results[0], results[1]))
            self.assertFalse(np.array_equal(results[1], results[2]))
        finally:
            for resource in reversed(resources):
                resource.release()
            context.release()
