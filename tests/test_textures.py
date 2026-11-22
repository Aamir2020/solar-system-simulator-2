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

    def test_distant_points_keep_colors_and_solar_dominance_with_effects_on_or_off(self):
        import numpy as np

        from solar_system_simulator.data.catalog import AU
        from solar_system_simulator.rendering.appearance import POINT_COLORS
        from solar_system_simulator.rendering.camera import Camera
        from solar_system_simulator.rendering.renderer import rgb
        camera = Camera()
        camera.top_down()
        camera.span = 2000*AU
        positions = np.column_stack((np.linspace(-700, 700, len(BODIES))*AU,
                                     np.zeros((len(BODIES), 2))))
        baseline = self.draw(camera, None, stars=False)
        points = camera.to_screen(positions, 160, 160)
        for effects in (False, True):
            with self.subTest(effects=effects):
                image = self.draw(camera, positions, stars=False, effects=effects)
                difference = image[:, :, :3].astype(float) - baseline[:, :, :3]
                flux, area = [], []
                for index, (x, y) in enumerate(points):
                    x, y = round(x), round(160-y)
                    patch = difference[y-6:y+6, x-6:x+6]
                    flux.append(patch.sum())
                    area.append(np.count_nonzero(np.linalg.norm(patch, axis=-1) > 10))
                    color = patch.reshape(-1, 3).sum(axis=0)
                    self.assertGreater(color.sum(), 10, BODIES[index].name)
                    expected = np.array(rgb(POINT_COLORS[index])) - baseline[y, x, :3]/255
                    np.testing.assert_allclose(color/color.max(), expected/expected.max(), atol=.04)
                self.assertGreater(flux[0], max(flux[1:])*3)
                self.assertGreater(area[0], max(area[1:]))
                self.assertTrue(np.all(image[:, :, 3] == 255))

    def test_sun_is_a_white_point_at_system_scale_and_textured_only_when_focused(self):
        import numpy as np

        from scripts.benchmark_physics import load_scenario
        from solar_system_simulator.data.catalog import AU
        from solar_system_simulator.rendering.camera import Camera
        from solar_system_simulator.rendering.scene import body_layout
        state = load_scenario().state
        camera = Camera()
        camera.top_down()
        camera.center = state.positions[0].copy()
        camera.span = 5*AU
        system_layout = body_layout(camera, state.positions, 160, 160)
        self.assertEqual(system_layout.point_weights[0], 1)
        system = self.draw(camera, state.positions, effects=False, stars=False)
        background = self.draw(camera, None, effects=False, stars=False)
        difference = system[:, :, :3].astype(int)-background[:, :, :3].astype(int)
        center = difference[74:86, 74:86]
        channels = center.reshape(-1, 3).sum(axis=0)
        self.assertLess(channels.max()-channels.min(), channels.max()*.08)

        camera.span = BODIES[0].radius*4
        focused_layout = body_layout(camera, state.positions, 160, 160)
        self.assertEqual(focused_layout.point_weights[0], 0)
        focused = self.draw(camera, state.positions, effects=False, stars=False)
        colors = np.unique(focused[50:110, 50:110, :3].reshape(-1, 3), axis=0)
        self.assertGreater(len(colors), 100)

    def test_unresolved_planet_is_hidden_behind_resolved_sphere(self):
        import numpy as np

        from solar_system_simulator.data.catalog import AU
        from solar_system_simulator.rendering.camera import Camera
        camera = Camera()
        camera.top_down()
        camera.span = BODIES[0].radius*5
        positions = np.tile([100*AU, 100*AU, 0.], (len(BODIES), 1))
        positions[0] = 0
        baseline = self.draw(camera, positions, physical=True, effects=False, stars=False)
        positions[3] = [0, 0, -3*BODIES[0].radius]
        behind = self.draw(camera, positions, physical=True, effects=False, stars=False)
        np.testing.assert_array_equal(baseline, behind)
        positions[3, 2] *= -1
        front = self.draw(camera, positions, physical=True, effects=False, stars=False)
        self.assertFalse(np.array_equal(baseline, front))

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

    def test_orbit_fades_toward_tail_without_brightening_from_older_laps(self):
        import numpy as np

        from solar_system_simulator.data.catalog import AU
        from solar_system_simulator.rendering.camera import Camera
        camera = Camera()
        camera.top_down()
        camera.span = 4*AU
        positions = np.tile([100*AU, 100*AU, 0.], (len(BODIES), 1))
        positions[0] = 0
        positions[3] = [AU, 0, 0]

        def history(turns):
            angles = np.linspace(0, turns*2*np.pi, turns*160+1)
            result = np.tile(positions, (len(angles), 1, 1))
            result[:, 3] = np.column_stack((np.cos(angles), np.sin(angles), angles*0))*AU
            return result

        options = {'physical': True, 'effects': False, 'stars': False}
        baseline = self.draw(camera, positions, **options)
        single = self.draw(camera, positions, history=history(1), **options)
        repeated = self.draw(camera, positions, history=history(3), **options)
        self.assertLessEqual(np.abs(single.astype(int)-repeated.astype(int)).max(), 1)
        difference = np.linalg.norm(single[:, :, :3].astype(float)-baseline[:, :, :3], axis=-1)
        y, x = np.mgrid[:160, :160]
        angle = np.arctan2(y+.5-80, x+.5-80) % (2*np.pi)
        tail = difference[(angle > .2*np.pi) & (angle < .4*np.pi)].sum()
        head = difference[(angle > 1.6*np.pi) & (angle < 1.8*np.pi)].sum()
        self.assertGreater(tail, 0)
        self.assertGreater(head, 3*tail)
        self.assertTrue(np.all(repeated[:, :, 3] == 255))
