"""Synthetic states for deterministic tests only; never shipped as application data."""
import json
from pathlib import Path
from solar_system_simulator.data.scenario import Scenario
from solar_system_simulator.physics.system import State


def sample_scenario():
    data = json.loads((Path(__file__).parent / 'fixtures/original_solver.json').read_text())
    return Scenario(State(**data['initial']), '2026-01-01T00:00:00',
                    'Synthetic test fixture — not NASA ephemerides')
