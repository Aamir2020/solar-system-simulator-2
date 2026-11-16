"""Reproducible timestep comparison using frozen NASA initial vectors, without network access."""
import argparse
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np

from solar_system_simulator.data.catalog import BODIES, DAY
from solar_system_simulator.data.horizons import parameters, parse_vectors
from solar_system_simulator.data.scenario import Scenario
from solar_system_simulator.physics.system import G, State, energy, step

FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/nasa_horizons_2026-01-01.json'


def load_scenario(path=FIXTURE):
    fixture = json.loads(Path(path).read_text())
    positions, velocities = [], []
    for body, record in zip(BODIES, fixture['responses'], strict=True):
        request = parameters(body.horizons_id, fixture['epoch_tdb'])
        if record['body'] != body.name or record['request'] != request:
            raise ValueError('NASA fixture body, epoch, or reference frame mismatch')
        position, velocity = parse_vectors(record['response'], float(request['TLIST']))
        positions.append(position)
        velocities.append(velocity)
    return Scenario(State(positions, velocities, [body.mass for body in BODIES]),
                    fixture['epoch_tdb'], 'Frozen NASA/JPL Horizons initial vectors (tests only)')


@dataclass
class Integration:
    positions: np.ndarray
    diagnostics: dict


def integrate(initial, days, dt):
    """Sample identical daily times for every fixed timestep, without the GUI or worker."""
    if days <= 0 or int(days) != days or not np.isfinite(dt) or dt <= 0:
        raise ValueError('Days must be a positive integer and timestep must be positive and finite')
    steps_per_day = round(DAY / dt)
    if steps_per_day < 1 or steps_per_day * dt != DAY:
        raise ValueError('Timestep must divide one day exactly')
    days = int(days)
    state = initial.copy()
    positions = np.empty((days + 1, *state.positions.shape))
    positions[0] = state.positions
    initial_energy = energy(state)
    initial_momentum = np.sum(state.masses[:, None] * state.velocities, axis=0)
    momentum_scale = np.sum(state.masses * np.linalg.norm(state.velocities, axis=1))
    initial_angular = np.sum(state.masses[:, None] * np.cross(state.positions, state.velocities), axis=0)
    angular_scale = np.linalg.norm(initial_angular)
    max_energy = max_momentum = max_angular = 0.
    started = perf_counter()
    for day in range(1, days + 1):
        for _ in range(steps_per_day):
            step(state, dt)
        positions[day] = state.positions
        energy_error = (energy(state) - initial_energy) / abs(initial_energy)
        max_energy = max(max_energy, abs(energy_error))
        momentum = np.sum(state.masses[:, None] * state.velocities, axis=0)
        angular = np.sum(state.masses[:, None] * np.cross(state.positions, state.velocities), axis=0)
        max_momentum = max(max_momentum, np.linalg.norm(momentum - initial_momentum) / momentum_scale)
        max_angular = max(max_angular, np.linalg.norm(angular - initial_angular) / angular_scale)
    diagnostics = {
        'dt_seconds': dt,
        'steps': days * steps_per_day,
        'runtime_seconds': perf_counter() - started,
        'max_sampled_relative_energy_error': float(max_energy),
        'final_relative_energy_error': float(energy_error),
        'max_sampled_scaled_momentum_error': float(max_momentum),
        'max_sampled_relative_angular_momentum_error': float(max_angular),
    }
    return Integration(positions, diagnostics)


def compare(trial, reference):
    # Subtract the Sun's position so this measures orbital error, including Z.
    trial_orbits = trial.positions - trial.positions[:, :1]
    reference_orbits = reference.positions - reference.positions[:, :1]
    errors_km = np.linalg.norm(trial_orbits - reference_orbits, axis=2) / 1000
    return {
        **trial.diagnostics,
        'max_sampled_heliocentric_position_error_km': float(errors_km.max()),
        'final_max_heliocentric_position_error_km': float(errors_km[-1].max()),
        'bodies': {body.name: {
            'max_sampled_position_error_km': float(errors_km[:, i].max()),
            'final_position_error_km': float(errors_km[-1, i]),
        } for i, body in enumerate(BODIES)},
    }


def benchmark(scenario, days=5 * 365):
    reference = integrate(scenario.state, days, 900.)
    reference_check = integrate(scenario.state, days, 1800.)
    trials = [compare(integrate(scenario.state, days, dt), reference)
              for dt in (DAY, 21600., 3600.)]
    return {
        'method': 'Fixed-step kick-drift-kick leapfrog, 3D Newtonian nine-body gravity',
        'initial_vectors': 'tests/fixtures/nasa_horizons_2026-01-01.json',
        'initial_vectors_source': 'https://ssd.jpl.nasa.gov/api/horizons.api',
        'epoch_tdb': scenario.epoch,
        'coordinate_frame': scenario.frame,
        'gravitational_constant_si': G,
        'masses_kg': {body.name: float(mass) for body, mass in
                      zip(BODIES, scenario.state.masses, strict=True)},
        'duration_days': days,
        'sampling_interval_days': 1,
        'scope': 'Numerical convergence within this model, not agreement with future NASA ephemerides. '
                 'Local masses are unchanged; moons and relativity are excluded. '
                 'Conservation errors and position differences are sampled daily.',
        'environment': {'python': platform.python_version(), 'numpy': np.__version__,
                        'platform': f'{platform.system()} {platform.machine()}'},
        'reference': reference.diagnostics,
        'reference_check_30_min_vs_15_min': compare(reference_check, reference),
        'timesteps': trials,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--years', type=int, default=5, help='Number of 365-day years (default: 5)')
    parser.add_argument('--output', type=Path, help='Also save the full JSON report')
    args = parser.parse_args()
    if args.years <= 0:
        parser.error('--years must be positive')
    report = benchmark(load_scenario(), days=args.years * 365)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f"{report['duration_days']} days from {report['epoch_tdb']}, 15-minute reference")
    print('Step       Max position difference (km)    Max relative energy error    Runtime (s)')
    for row in report['timesteps']:
        print(f"{row['dt_seconds'] / 3600:>4g} hours {row['max_sampled_heliocentric_position_error_km']:>27,.1f}"
              f" {row['max_sampled_relative_energy_error']:>28.3e} {row['runtime_seconds']:>14.2f}")
    check = report['reference_check_30_min_vs_15_min']
    print('30-minute / 15-minute reference difference: '
          f"{check['max_sampled_heliocentric_position_error_km']:,.1f} km")


if __name__ == '__main__':
    main()
