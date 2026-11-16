"""Check inclined eccentric orbits against the analytic two-body Kepler solution."""
import unittest

import numpy as np

from solar_system_simulator.data.catalog import AU
from solar_system_simulator.physics.system import G, State, energy, step


class EccentricOrbitTests(unittest.TestCase):
    eccentricity = .6
    inclination = .7
    masses = np.array([1.989e30, 5.972e24])

    def exact_state(self, mean_anomaly):
        # Solve E - e sin(E) = M, then rotate the ellipse into an inclined plane.
        anomaly = mean_anomaly % (2*np.pi)
        for _ in range(20):
            correction = ((anomaly - self.eccentricity*np.sin(anomaly) - mean_anomaly % (2*np.pi))
                          / (1 - self.eccentricity*np.cos(anomaly)))
            anomaly -= correction
            if abs(correction) < 1e-14:
                break
        n = np.sqrt(G*self.masses.sum()/AU**3)
        minor = np.sqrt(1 - self.eccentricity**2)
        position = AU*np.array([np.cos(anomaly) - self.eccentricity,
                               minor*np.sin(anomaly), 0.])
        velocity = AU*n/(1 - self.eccentricity*np.cos(anomaly))*np.array(
            [-np.sin(anomaly), minor*np.cos(anomaly), 0.])
        angle = self.inclination
        rotation = np.array([[1, 0, 0], [0, np.cos(angle), -np.sin(angle)],
                             [0, np.sin(angle), np.cos(angle)]])
        fractions = np.array([-self.masses[1], self.masses[0]]) / self.masses.sum()
        return State(fractions[:, None] * (rotation @ position),
                     fractions[:, None] * (rotation @ velocity), self.masses), 2*np.pi/n

    def test_eccentric_orbit_converges_to_kepler_solution(self):
        initial, period = self.exact_state(0.)
        errors = []
        # Non-integer orbit counts test more than a coincidental return to perihelion.
        for steps_per_orbit in (2000, 4000, 8000):
            state = initial.copy()
            max_error = 0.
            for quarter in range(1, 14):
                for _ in range(steps_per_orbit // 4):
                    step(state, period / steps_per_orbit)
                exact, _ = self.exact_state(quarter*np.pi/2)
                max_error = max(max_error, np.linalg.norm(
                    (state.positions[1] - state.positions[0]) -
                    (exact.positions[1] - exact.positions[0])))
            errors.append(max_error)
        self.assertGreater(errors[0] / errors[1], 3.8)
        self.assertGreater(errors[1] / errors[2], 3.8)
        self.assertLess(errors[-1] / AU, .001)

    def test_eccentric_energy_remains_bounded_and_angular_momentum_is_conserved(self):
        state, period = self.exact_state(0.)
        initial_energy = energy(state)
        initial_angular = np.sum(state.masses[:, None]*np.cross(state.positions, state.velocities), axis=0)
        orbit_maxima = []
        for _ in range(10):
            maximum = 0.
            for _ in range(2000):
                step(state, period/2000)
                maximum = max(maximum, abs((energy(state) - initial_energy)/initial_energy))
            orbit_maxima.append(maximum)
        self.assertLess(max(orbit_maxima), 1e-4)
        self.assertLess(max(orbit_maxima[1:]), orbit_maxima[0]*1.05)
        angular = np.sum(state.masses[:, None]*np.cross(state.positions, state.velocities), axis=0)
        self.assertLess(np.linalg.norm(angular - initial_angular) / np.linalg.norm(initial_angular), 1e-12)
