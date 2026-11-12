"""Pairwise gravity and kick–drift–kick leapfrog, preserving the original method."""
from dataclasses import dataclass
import numpy as np

G = 6.67430e-11


@dataclass
class State:
    positions: np.ndarray
    velocities: np.ndarray
    masses: np.ndarray
    elapsed: float = 0.0

    def __post_init__(self):
        self.positions = np.array(self.positions, dtype=np.float64, copy=True)
        self.velocities = np.array(self.velocities, dtype=np.float64, copy=True)
        self.masses = np.array(self.masses, dtype=np.float64, copy=True)
        n = len(self.masses)
        if self.positions.shape != (n, 2) or self.velocities.shape != (n, 2) or not n:
            raise ValueError("State requires non-empty (N, 2) positions and velocities.")
        if self.masses.shape != (n,) or np.any(self.masses <= 0):
            raise ValueError("Masses must be a positive one-dimensional array.")
        if not all(np.isfinite(a).all() for a in
                   (self.positions, self.velocities, self.masses)):
            raise ValueError("State contains non-finite values.")
        if not np.isfinite(self.elapsed):
            raise ValueError("Elapsed time must be finite.")

    def copy(self):
        return State(self.positions, self.velocities, self.masses, self.elapsed)


def accelerations(positions, masses):
    """No softening: coincident distinct bodies are an explicit unsupported collision."""
    delta = positions[None, :, :] - positions[:, None, :]
    squared = np.einsum("ijk,ijk->ij", delta, delta)
    np.fill_diagonal(squared, np.inf)
    if np.any(squared == 0):
        raise ValueError("Two bodies occupy the same position; collisions are unsupported.")
    inverse_cube = squared ** -1.5
    return G * np.einsum("ij,ijk,j->ik", inverse_cube, delta, masses)


def step(state: State, dt: float):
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("Integration timestep must be finite and positive.")
    half_velocity = state.velocities + 0.5 * dt * accelerations(state.positions, state.masses)
    positions = state.positions + dt * half_velocity
    velocities = half_velocity + 0.5 * dt * accelerations(positions, state.masses)
    if not np.isfinite(positions).all() or not np.isfinite(velocities).all():
        raise ValueError("Integration became non-finite. Restart with a smaller timestep.")
    state.positions = positions
    state.velocities = velocities
    state.elapsed += dt


def energy(state):
    kinetic = 0.5 * np.sum(state.masses * np.sum(state.velocities ** 2, axis=1))
    potential = 0.0
    for i in range(len(state.masses)):
        distance = np.linalg.norm(state.positions[i + 1:] - state.positions[i], axis=1)
        potential -= G * state.masses[i] * np.sum(state.masses[i + 1:] / distance)
    return float(kinetic + potential)
