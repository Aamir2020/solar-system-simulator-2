"""Three-year convergence and conservation checks on genuine NASA initial vectors."""
import unittest
from itertools import pairwise

from scripts.benchmark_physics import benchmark, load_scenario
from solar_system_simulator.data.catalog import AU
from solar_system_simulator.physics.system import DEFAULT_DT


class SolarSystemAccuracyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenario = load_scenario()
        cls.report = benchmark(cls.scenario, days=3*365)

    def test_nasa_initial_state_retains_inclined_orbits(self):
        state = self.scenario.state
        self.assertEqual(state.positions.shape, (9, 3))
        self.assertEqual(state.velocities.shape, (9, 3))
        self.assertGreater(abs(state.positions[1, 2]), .01*AU)
        self.assertGreater(abs(state.velocities[1, 2]), 100.)

    def test_nine_body_position_errors_show_second_order_convergence(self):
        trials = self.report['timesteps']
        reference_dt = self.report['reference']['dt_seconds']
        for coarse, fine in pairwise(trials):
            observed = (coarse['max_sampled_heliocentric_position_error_km'] /
                        fine['max_sampled_heliocentric_position_error_km'])
            expected = ((coarse['dt_seconds']**2 - reference_dt**2) /
                        (fine['dt_seconds']**2 - reference_dt**2))
            self.assertLess(abs(observed/expected - 1), .15)

    def test_default_limits_position_and_energy_error_over_three_years(self):
        default = next(row for row in self.report['timesteps'] if row['dt_seconds'] == DEFAULT_DT)
        self.assertLess(default['max_sampled_heliocentric_position_error_km'], 30000.)
        self.assertLess(default['max_sampled_relative_energy_error'], 1e-8)
        reference_difference = self.report['reference_check_30_min_vs_15_min']
        self.assertLess(reference_difference['max_sampled_heliocentric_position_error_km'],
                        .3*default['max_sampled_heliocentric_position_error_km'])

    def test_nine_body_momentum_and_angular_momentum_are_conserved(self):
        for trial in self.report['timesteps']:
            with self.subTest(dt=trial['dt_seconds']):
                self.assertLess(trial['max_sampled_scaled_momentum_error'], 1e-12)
                self.assertLess(trial['max_sampled_relative_angular_momentum_error'], 1e-12)
                self.assertLess(trial['max_sampled_relative_energy_error'], 1e-5)
