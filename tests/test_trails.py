"""Orbit ribbons must end at the displayed planet and clip safely in perspective."""
import unittest
from types import SimpleNamespace

import numpy as np

from solar_system_simulator.data.catalog import AU, BODIES
from solar_system_simulator.rendering.camera import Camera
from solar_system_simulator.rendering.scene import orbit_trail, trail_history, trail_vertices
from solar_system_simulator.rendering.viewport import Viewport

DAY = 86400.


def positions_at(days):
    origins = np.column_stack((np.arange(len(BODIES))*AU, np.zeros((len(BODIES), 2))))
    return origins + np.array([.0005*AU, .00025*AU, .0001*AU])*days


def snapshot(days, history_days, published):
    return SimpleNamespace(generation=0, elapsed=days*DAY, published=published,
        positions=positions_at(days), trails=np.array([positions_at(day) for day in history_days]),
        trail_times=np.array(history_days)*DAY)


class TrailTests(unittest.TestCase):
    def view(self, previous, current, paused=False, limit=800):
        camera = Camera()
        camera.span = camera.target_span = .00005*AU
        return SimpleNamespace(snapshot=current, previous=previous, paused=paused,
            positions=None, render_elapsed=current.elapsed, camera=camera, trail_length=limit)

    def check_geometry(self, view, now):
        Viewport._interpolate(view, now)
        view.camera.animate(1/60, follow=view.positions[3])
        history = trail_history(view.snapshot, view.render_elapsed, view.positions, view.trail_length)
        np.testing.assert_array_equal(history[-1], view.positions)
        self.assertLessEqual(len(history), view.trail_length)
        # Every retained point must be at or behind the displayed time along this trajectory.
        direction = np.array([1., .5, .2])
        self.assertTrue(np.all(np.einsum('tij,j->ti', history-view.positions, direction) <= .01))
        vertices = trail_vertices(view.camera, history[:, 3], 1200, 800).reshape(-1, 6, 6)
        self.assertGreater(len(vertices), 0)
        expected = view.camera.to_view(view.positions[3])/view.camera.distance
        np.testing.assert_allclose(vertices[-1, 5, :3], expected, atol=1e-7)
        self.assertTrue(np.isfinite(vertices).all())
        self.assertTrue(np.all(vertices[:, :, 2] > 0))

    def test_trails_do_not_lead_interpolated_planets_when_updates_are_skipped(self):
        previous = snapshot(2, [0, 1, 2], 99.)
        current = snapshot(8, list(range(9)), 100.)
        original = current.trails.copy()
        for alpha in (0., .25, .5, .9, 1.):
            with self.subTest(alpha=alpha):
                self.check_geometry(self.view(previous, current), 100.+alpha)
        np.testing.assert_array_equal(current.trails, original)

    def test_subday_updates_connect_sampled_trail_to_planet(self):
        previous = snapshot(2, [0, 1, 2], 99.)
        current = snapshot(2.5, [0, 1, 2], 100.)
        for paused in (False, True):
            with self.subTest(paused=paused):
                self.check_geometry(self.view(previous, current, paused), 100.5)

    def test_clipping_precedes_history_limit(self):
        self.check_geometry(self.view(snapshot(2, [0, 1, 2], 99.),
                                      snapshot(8, list(range(9)), 100.), limit=3), 100.)

    def test_initial_state_has_no_trail_and_reset_discards_old_interpolation(self):
        initial = snapshot(0, [0], 101.)
        initial.generation = 1
        view = self.view(snapshot(7, [0, 7], 99.), snapshot(8, [0, 8], 100.))
        Viewport.accept_snapshot(view, initial)
        self.assertIsNone(view.previous)
        Viewport._interpolate(view, 101.)
        history = trail_history(initial, view.render_elapsed, view.positions, 800)
        self.assertEqual(len(trail_vertices(view.camera, history[:, 3], 1200, 800)), 0)
        np.testing.assert_array_equal(view.positions, initial.positions)

    def test_trail_crossing_the_eye_plane_is_clipped_and_behind_camera_is_hidden(self):
        camera = Camera()
        camera.top_down()
        distance = camera.distance
        crossing = np.array([[0, 0, 2*distance], [.1*distance, 0, 0.]])
        vertices = trail_vertices(camera, crossing, 1200, 800)
        self.assertGreater(len(vertices), 0)
        self.assertTrue(np.isfinite(vertices).all())
        self.assertTrue(np.all(vertices[:, 2] >= 1e-5-1e-10))
        crossing[:, 2] += 3*distance
        self.assertEqual(len(trail_vertices(camera, crossing, 1200, 800)), 0)

    def test_bends_share_edges_instead_of_overlapping_independent_quads(self):
        camera = Camera()
        camera.top_down()
        path = np.array([[-.3, -.2, 0], [0, -.2, 0], [0, .2, 0], [.3, .2, 0]])*camera.span
        vertices = trail_vertices(camera, path, 1200, 800).reshape(-1, 6, 6)
        self.assertEqual(len(vertices), 3)
        np.testing.assert_array_equal(vertices[:-1, 2], vertices[1:, 0])
        np.testing.assert_array_equal(vertices[:-1, 5], vertices[1:, 1])

    def test_width_and_fade_grow_toward_planet_by_distance_not_sample_count(self):
        camera = Camera()
        camera.top_down()
        path = np.array([[-.4, 0, 0], [-.3, 0, 0], [.4, 0, 0]])*camera.span
        vertices = trail_vertices(camera, path, 1200, 800).reshape(-1, 6, 6)
        self.assertAlmostEqual(vertices[0, 0, 5], 0.)
        self.assertAlmostEqual(vertices[0, 2, 5], .125)
        self.assertAlmostEqual(vertices[-1, 5, 5], 1.)
        offsets = np.linalg.norm(vertices[:, :, 3:5], axis=-1)
        self.assertLess(offsets[0, 0], offsets[0, 2])
        self.assertLess(offsets[0, 2], offsets[-1, 5])

    def test_only_latest_revolution_is_retained_about_moving_sun(self):
        # Inclination and solar motion must not change where a lap is cut.
        angles = np.linspace(0, 6*np.pi, 241)
        orbit = np.column_stack((np.cos(angles), .8*np.sin(angles), .6*np.sin(angles)))*AU
        centers = np.column_stack((angles*.02*AU, angles*0, angles*.01*AU))
        path = orbit + centers
        original = path.copy()
        result = orbit_trail(path, centers)
        np.testing.assert_allclose(result, path[-81:], atol=.002)
        np.testing.assert_array_equal(result[-1], path[-1])
        np.testing.assert_array_equal(path, original)
        partial = orbit_trail(path[:40], centers[:40])
        np.testing.assert_array_equal(partial, path[:40])

    def test_revolution_boundary_between_samples_keeps_interpolated_tail(self):
        angles = np.linspace(0, 7, 30)
        path = np.column_stack((np.cos(angles), np.sin(angles), angles*0))*AU
        result = orbit_trail(path, np.zeros_like(path))
        start = np.searchsorted(angles, angles[-1]-2*np.pi)-1
        fraction = (angles[-1]-2*np.pi-angles[start])/(angles[start+1]-angles[start])
        np.testing.assert_allclose(result[0], path[start]+fraction*(path[start+1]-path[start]), atol=.001)
        np.testing.assert_array_equal(result[1:], path[start+1:])

    def test_stationary_and_repeated_samples_are_finite(self):
        camera = Camera()
        stationary = np.zeros((8, 3))
        self.assertEqual(len(trail_vertices(camera, stationary, 1200, 800)), 0)
        path = np.array([[-.2, 0, 0], [0, 0, 0], [0, 0, 0], [.2, 0, 0]])*camera.span
        self.assertTrue(np.isfinite(trail_vertices(camera, path, 1200, 800)).all())
