import importlib.util
import unittest
from hashlib import sha256
from importlib.resources import files

from solar_system_simulator.data.catalog import BODIES
from solar_system_simulator.rendering.textures import image_data, texture_manifest


class TextureAssetTests(unittest.TestCase):
    def test_every_body_has_its_original_attributed_image(self):
        manifest = texture_manifest()
        self.assertEqual(set(manifest), {body.name for body in BODIES} |
                         {'Sky', 'Earth night', 'Earth clouds', 'Saturn rings'})
        directory = files('solar_system_simulator').joinpath('assets/textures')
        for name, entry in manifest.items():
            with self.subTest(body=name):
                data = directory.joinpath(entry['file']).read_bytes()
                self.assertEqual(sha256(data).hexdigest(), entry['sha256'])
                self.assertTrue(data.startswith((b'\xff\xd8', b'\x89PNG')))
                self.assertTrue(entry['url'].startswith('https://www.solarsystemscope.com/'))
        attribution = directory.joinpath('ATTRIBUTION.md').read_text()
        self.assertIn('CC BY 4.0', attribution)
        self.assertIn('Solar System Scope', attribution)

    @unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 is not installed')
    def test_all_images_decode_to_full_resolution_rgba(self):
        for name, entry in texture_manifest().items():
            with self.subTest(body=name):
                size, data = image_data(name)
                self.assertEqual(size, (entry['width'], entry['height']))
                self.assertEqual(len(data), size[0]*size[1]*4)


@unittest.skipUnless(importlib.util.find_spec('moderngl') and importlib.util.find_spec('PySide6'),
                     'ModernGL and PySide6 are required')
class TextureRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import moderngl

        from solar_system_simulator.rendering.renderer import SceneRenderer
        try:
            cls.context = moderngl.create_context(standalone=True, backend='egl')
        except Exception as exc:
            raise unittest.SkipTest(f'Headless EGL context unavailable: {exc}') from exc
        cls.renderer = SceneRenderer(cls.context)
        cls.framebuffer = cls.context.simple_framebuffer((160, 160), components=4)

    @classmethod
    def tearDownClass(cls):
        cls.renderer.release()
        cls.framebuffer.release()
        cls.context.release()

    def draw(self, camera, positions, **kwargs):
        import numpy as np
        self.framebuffer.use()
        self.context.viewport = (0, 0, 160, 160)
        self.renderer.draw(camera, positions, 160, 160, **kwargs)
        return np.frombuffer(self.framebuffer.read(components=4), dtype='u1').reshape(160, 160, 4).copy()

    def test_production_meshes_render_distinct_textured_planets_and_hemispheres(self):
        import numpy as np

        from scripts.benchmark_physics import load_scenario
        from solar_system_simulator.rendering.camera import Camera
        state = load_scenario().state
        camera = Camera()
        camera.pitch = 0.
        images = []
        for index in (3, 4, 5):
            camera.center = state.positions[index].copy()
            camera.span = BODIES[index].radius*4
            image = self.draw(camera, state.positions, physical=True, effects=False, stars=False)
            colors = np.unique(image[55:105, 55:105, :3].reshape(-1, 3), axis=0)
            self.assertGreater(len(colors), 100)
            images.append(image)
        self.assertFalse(np.array_equal(images[0], images[1]))
        self.assertFalse(np.array_equal(images[1], images[2]))
        camera.center = state.positions[3].copy()
        camera.span = BODIES[3].radius*4
        camera.orbit(300, 0)
        other_hemisphere = self.draw(camera, state.positions, physical=True, effects=False, stars=False)
        self.assertFalse(np.array_equal(images[0], other_hemisphere))

    def test_sky_rotates_with_view_but_does_not_move_with_pan_or_zoom(self):
        import numpy as np

        from solar_system_simulator.data.catalog import AU
        from solar_system_simulator.rendering.camera import Camera
        camera = Camera()
        initial = self.draw(camera, None, sky_brightness=1.)
        camera.center += [AU, -2*AU, 3*AU]
        camera.span *= .02
        moved = self.draw(camera, None, sky_brightness=1.)
        np.testing.assert_array_equal(initial, moved)
        camera.orbit(120, 60)
        rotated = self.draw(camera, None, sky_brightness=1.)
        self.assertFalse(np.array_equal(initial, rotated))
        hidden = self.draw(camera, None, stars=False)
        self.assertGreater(np.count_nonzero(initial[:, :, :3] != hidden[:, :, :3]), 100)

    def test_planets_occlude_each_other_independently_of_draw_order(self):
        import numpy as np

        from solar_system_simulator.data.catalog import AU
        from solar_system_simulator.rendering.camera import Camera
        camera = Camera()
        camera.top_down()
        camera.span = BODIES[0].radius*5
        positions = np.tile([100*AU, 100*AU, 0.], (len(BODIES), 1))
        positions[0] = 0
        alone = self.draw(camera, positions, effects=False, stars=False)
        positions[3] = [0, 0, -3*BODIES[0].radius]
        behind = self.draw(camera, positions, effects=False, stars=False)
        np.testing.assert_array_equal(alone[80, 80], behind[80, 80])
        positions[3, 2] *= -1
        front = self.draw(camera, positions, effects=False, stars=False)
        self.assertFalse(np.array_equal(alone[80, 80], front[80, 80]))

    def test_translucent_rings_and_sun_glow_keep_the_viewport_opaque(self):
        import numpy as np

        from scripts.benchmark_physics import load_scenario
        from solar_system_simulator.rendering.camera import Camera
        state = load_scenario().state
        camera = Camera()
        for index in (0, 6):
            with self.subTest(body=BODIES[index].name):
                camera.center = state.positions[index].copy()
                camera.span = BODIES[index].radius*6
                baseline = self.draw(camera, state.positions, physical=True, effects=False)
                image = self.draw(camera, state.positions, physical=True, effects=True)
                self.assertGreater(np.count_nonzero(image[:, :, :3] != baseline[:, :, :3]), 100)
                self.assertTrue(np.all(image[:, :, 3] == 255),
                                f'Transparent viewport pixels: minimum alpha {image[:, :, 3].min()}')
