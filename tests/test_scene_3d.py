"""Camera, mesh, selection, and depth invariants for a solar-system-scale scene."""
import unittest

import numpy as np

from solar_system_simulator.data.catalog import AU, BODIES
from solar_system_simulator.rendering.camera import Camera
from solar_system_simulator.rendering.geometry import ring_mesh, sphere_mesh
from solar_system_simulator.rendering.scene import body_layout, pick_sphere


class Scene3DTests(unittest.TestCase):
    def test_screen_ray_passes_through_projected_world_point(self):
        camera = Camera()
        camera.center = np.array([AU, -2*AU, .1*AU])
        camera.orbit(120, 35)
        point = camera.center + [.2*AU, .1*AU, .3*AU]
        screen = camera.to_screen(point, 1200, 800)
        origin, ray = camera.ray(screen, 1200, 800)
        expected = point-origin
        expected /= np.linalg.norm(expected)
        np.testing.assert_allclose(ray, expected, atol=1e-14)

    def test_orbit_preserves_target_distance_and_has_a_finite_basis_at_poles(self):
        camera = Camera()
        center = camera.center.copy()
        distance = camera.distance
        for dy in (500, -1000, 300, -30):
            camera.orbit(75, dy)
            self.assertAlmostEqual(np.linalg.norm(camera.eye-camera.center)/distance, 1.)
            np.testing.assert_allclose(camera.view_rotation @ camera.view_rotation.T, np.eye(3), atol=1e-14)
            np.testing.assert_array_equal(camera.center, center)

    def test_top_down_and_oblique_views_project_actual_z(self):
        camera = Camera()
        camera.top_down()
        points = np.array([[AU, 0, 0], [AU, 0, AU]])
        screen = camera.to_screen(points, 1200, 800)
        self.assertGreater(screen[1, 0], screen[0, 0])  # Nearer objects appear larger.
        camera.perspective()
        oblique = camera.to_screen(points, 1200, 800)
        self.assertGreater(abs(oblique[0, 1]-oblique[1, 1]), 20)

    def test_camera_relative_projection_stays_precise_at_neptune_distances(self):
        camera = Camera()
        camera.span = .00005*AU
        local = np.array([[0., 0., 0.], [1000., -2000., 3000.]])
        initial = camera.to_screen(local, 1200, 800)
        shift = np.array([30*AU, -20*AU, AU])
        camera.center = shift.copy()
        shifted = camera.to_screen(local+shift, 1200, 800)
        np.testing.assert_allclose(initial, shifted, atol=1e-5)
        np.testing.assert_array_equal(camera.to_view(shift)/camera.distance, [0, 0, 1])

    def test_behind_camera_is_not_projected_or_pickable(self):
        camera = Camera()
        camera.top_down()
        point = camera.eye + [0, 0, AU]
        self.assertTrue(np.isnan(camera.to_screen(point, 1200, 800)).all())
        self.assertIsNone(pick_sphere(camera, point[None], np.array([1e6]), [600,400], 1200,800))

    def test_free_camera_cannot_zoom_inside_a_planet(self):
        camera = Camera()
        positions = np.array([camera.eye.copy()])
        original = positions.copy()
        radii = np.array([1e7])
        camera.keep_outside(positions, radii)
        self.assertGreaterEqual(np.linalg.norm(camera.eye-positions[0]), radii[0]*1.049)
        np.testing.assert_array_equal(positions, original)

    def test_picking_uses_nearest_surface_instead_of_body_center(self):
        camera = Camera()
        camera.top_down()
        d = camera.distance
        positions = np.array([[0., 0., -.1*d], [0., 0., 0.]])
        radii = np.array([.3*d, .02*d])
        self.assertEqual(pick_sphere(camera, positions, radii, [600,400], 1200,800), 0)

    def test_occluded_planet_hidden_and_physical_state_is_unchanged(self):
        camera = Camera()
        camera.top_down()
        positions = np.tile([100*AU, 0., 0.], (len(BODIES), 1))
        positions[0] = 0
        positions[3] = [0, 0, -.1*AU]
        original = positions.copy()
        layout = body_layout(camera, positions, 1200, 800)
        self.assertTrue(layout.visible[0])
        self.assertFalse(layout.visible[3])
        self.assertTrue(np.all(layout.world_radii >= [b.radius for b in BODIES]))
        np.testing.assert_array_equal(positions, original)

    def test_sphere_has_closed_uv_seam_unit_normals_and_valid_triangle_indices(self):
        vertices, indices = sphere_mesh()
        np.testing.assert_allclose(np.linalg.norm(vertices[:, :3], axis=1), 1., atol=1e-7)
        self.assertTrue(np.all((vertices[:, 3:] >= 0) & (vertices[:, 3:] <= 1)))
        self.assertLess(indices.max(), len(vertices))
        seam_a = vertices[vertices[:, 3] == 0]
        seam_b = vertices[vertices[:, 3] == 1]
        np.testing.assert_allclose(seam_a[:, :3], seam_b[:, :3], atol=1e-7)
        self.assertEqual(len(indices) % 3, 0)
        rings, indices = ring_mesh()
        self.assertTrue(np.all(rings[:, 2] == 0))
        self.assertLess(indices.max(), len(rings))
        self.assertGreater(np.linalg.norm(rings[:, :2], axis=1).min(), 1.)
