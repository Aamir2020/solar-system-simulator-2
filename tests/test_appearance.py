"""Distant-body brightness follows reflected-light geometry before display compression."""
import unittest

import numpy as np

from solar_system_simulator.data.catalog import AU, BODIES
from solar_system_simulator.rendering.appearance import (
    GEOMETRIC_ALBEDOS,
    MAXIMUM_PLANET_BRIGHTNESS,
    MINIMUM_POINT_BRIGHTNESS,
    lambert_phase,
    point_brightness,
    reflected_fluxes,
)


class AppearanceTests(unittest.TestCase):
    def positions(self, earth_distance=AU):
        positions = np.tile([100*AU, 100*AU, 0.], (len(BODIES), 1))
        positions[0] = 0
        positions[3] = [earth_distance, 0, 0]
        return positions

    def test_lambert_phase_has_full_quarter_and_dark_endpoints(self):
        values = lambert_phase(np.array([0., np.pi/2, np.pi]))
        np.testing.assert_allclose(values, [1., 1/np.pi, 0.], atol=1e-15)

    def test_flux_uses_phase_and_both_inverse_square_distances(self):
        positions = self.positions()
        full = reflected_fluxes(positions, [.5*AU, 0, 0])[2]
        quarter = reflected_fluxes(positions, [AU, .5*AU, 0])[2]
        dark = reflected_fluxes(positions, [1.5*AU, 0, 0])[2]
        self.assertAlmostEqual(full, 4.)
        self.assertAlmostEqual(full/quarter, np.pi)
        self.assertLess(dark, 1e-14)

        twice_solar_distance = reflected_fluxes(
            self.positions(2*AU), [1.5*AU, 0, 0])[2]
        half_observer_distance = reflected_fluxes(positions, [.75*AU, 0, 0])[2]
        self.assertAlmostEqual(twice_solar_distance/full, .25)
        self.assertAlmostEqual(half_observer_distance/full, 4.)

    def test_flux_uses_radius_and_jpl_geometric_albedo(self):
        positions = np.tile([AU, 0, 0.], (len(BODIES), 1))
        positions[0] = 0
        fluxes = reflected_fluxes(positions, [.5*AU, 0, 0])
        expected = (GEOMETRIC_ALBEDOS[1:]/GEOMETRIC_ALBEDOS[3] *
                    (np.array([body.radius for body in BODIES[1:]])/BODIES[3].radius)**2 * 4)
        np.testing.assert_allclose(fluxes, expected, rtol=1e-14)

    def test_display_compression_preserves_solar_dominance_and_visibility(self):
        positions = self.positions()
        levels = point_brightness(positions, [2000*AU, 0, 0])
        self.assertEqual(levels[0], 1.)
        self.assertTrue(np.all(levels[1:] >= MINIMUM_POINT_BRIGHTNESS))
        self.assertTrue(np.all(levels[1:] <= MAXIMUM_PLANET_BRIGHTNESS))


if __name__ == '__main__':
    unittest.main()
