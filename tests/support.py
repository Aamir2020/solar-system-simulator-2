"""Synthetic states for deterministic tests only; never shipped as application data."""
import json
from pathlib import Path
import numpy as np
from solar_system_simulator.data.scenario import Scenario
from solar_system_simulator.physics.system import State


def sample_scenario():
    data = json.loads((Path(__file__).parent / 'fixtures/original_solver.json').read_text())
    initial = data['initial']
    # Embed the original planar regression fixture in 3D without altering its values.
    for name in ('positions', 'velocities'):
        initial[name] = np.pad(initial[name], ((0, 0), (0, 1)))
    return Scenario(State(**initial), '2026-01-01T00:00:00',
                    'Synthetic test fixture — not NASA ephemerides')
