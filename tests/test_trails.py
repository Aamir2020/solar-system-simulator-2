"""Orbit geometry must use the same simulation time as the displayed planets."""
from types import SimpleNamespace
from unittest.mock import Mock
import unittest

import numpy as np

from solar_system_simulator.data.catalog import AU, BODIES
from solar_system_simulator.rendering.camera import Camera
from solar_system_simulator.rendering.viewport import Viewport


DAY = 86400.


def positions_at(days):
    origins = np.column_stack((np.arange(len(BODIES)) * AU, np.zeros((len(BODIES), 2))))
    return origins + np.array([.0005 * AU, .00025 * AU, .0001 * AU]) * days


def snapshot(days, history_days, published):
    return SimpleNamespace(
        generation=0, elapsed=days * DAY, published=published,
        positions=positions_at(days),
        trails=np.array([positions_at(day) for day in history_days]),
        trail_times=np.array(history_days) * DAY,
    )


class TrailTests(unittest.TestCase):
    def view(self, previous, current, paused=False, limit=800):
        camera = Camera()
        camera.span = .00005 * AU  # Maximum magnification exposes any timing mismatch.
        return SimpleNamespace(
            snapshot=current, previous=previous, paused=paused, positions=None,
            render_elapsed=current.elapsed, camera=camera, trail_length=limit,
            trail_program={'viewport': SimpleNamespace(value=None),
                           'color': SimpleNamespace(value=None)},
            trail_buffer=Mock(), trail_vao=Mock(),
        )

    def check_geometry(self, view, now):
        Viewport._interpolate(view, now)
        view.camera.animate(1/60, follow=view.positions[3])
        Viewport._draw_trails(view, 1200, 800)
        self.assertEqual(view.trail_buffer.write.call_count, len(BODIES))
        for index, call in enumerate(view.trail_buffer.write.call_args_list):
            vertices = np.frombuffer(call.args[0], dtype='f4').reshape(-1, 6, 4)
            # The last two corners straddle the center of the planet, at any zoom.
            end = (vertices[-1, 2, :2] + vertices[-1, 5, :2]) / 2
            planet = view.camera.to_screen(view.positions[index], 1200, 800)
            np.testing.assert_allclose(end, planet, atol=.01, rtol=0)
            # No part of the line's center path may lead the planet along its motion.
            starts = (vertices[:, 0, :2] + vertices[:, 1, :2]) / 2
            ends = (vertices[:, 2, :2] + vertices[:, 5, :2]) / 2
            for points in (starts, ends):
                self.assertTrue(np.all((points - planet) @ [1., -.5] <= .02))
            self.assertLessEqual(len(vertices), view.trail_length - 1)

    def test_trails_do_not_lead_interpolated_planets_when_updates_are_skipped(self):
        # A fast worker can publish several days beyond the last displayed snapshot.
        previous = snapshot(2, [0, 1, 2], 99.)
        current = snapshot(8, list(range(9)), 100.)
        original = current.trails.copy()
        for alpha in (0., .25, .5, .9, 1.):
            with self.subTest(alpha=alpha):
                self.check_geometry(self.view(previous, current), 100. + alpha)
        np.testing.assert_array_equal(current.trails, original)

    def test_subday_updates_connect_sampled_trail_to_planet(self):
        previous = snapshot(2, [0, 1, 2], 99.)
        current = snapshot(2.5, [0, 1, 2], 100.)
        for paused in (False, True):
            with self.subTest(paused=paused):
                self.check_geometry(self.view(previous, current, paused), 100.5)

    def test_clipping_precedes_history_limit(self):
        previous = snapshot(2, [0, 1, 2], 99.)
        current = snapshot(8, list(range(9)), 100.)
        self.check_geometry(self.view(previous, current, limit=3), 100.)

    def test_initial_state_has_no_trail_and_reset_discards_old_interpolation(self):
        initial = snapshot(0, [0], 101.)
        initial.generation = 1
        view = self.view(snapshot(7, [0, 7], 99.), snapshot(8, [0, 8], 100.))
        Viewport.accept_snapshot(view, initial)
        self.assertIsNone(view.previous)
        Viewport._interpolate(view, 101.)
        Viewport._draw_trails(view, 1200, 800)
        view.trail_buffer.write.assert_not_called()
        np.testing.assert_array_equal(view.positions, initial.positions)
