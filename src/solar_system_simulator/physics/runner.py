"""Bounded simulation worker; authoritative state never enters the GUI thread."""
from collections import deque
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Condition, Thread
from time import monotonic
import numpy as np
from .system import State, step


@dataclass(frozen=True)
class Snapshot:
    generation: int
    elapsed: float
    positions: np.ndarray
    velocities: np.ndarray
    trails: np.ndarray
    published: float
    achieved_rate: float


def readonly(array):
    result = np.array(array, dtype=np.float64, copy=True)
    result.flags.writeable = False
    return result


class StepBudget:
    """Retain fractional step debt, cap work after stalls instead of runaway catch-up."""
    def __init__(self):
        self.debt = 0.0

    def consume(self, wall_seconds, rate, dt, limit=256):
        self.debt += max(0.0, min(wall_seconds, 0.25)) * rate
        count = min(int(self.debt / dt), limit)
        self.debt -= count * dt
        self.debt = min(self.debt, dt * limit)
        return count


class SimulationRunner:
    def __init__(self, state: State | None = None, dt=86400.0, trail_limit=1500):
        self.condition = Condition()
        self.state = state.copy() if state is not None else None
        self.dt = dt
        self.rate = 30 * 86400.0
        self.paused = True
        self.generation = 0
        self.stopping = False
        self.single_steps = 0
        self.budget = StepBudget()
        self.history = deque([] if state is None else [state.positions.copy()], maxlen=trail_limit)
        self.last_sample = state.elapsed if state is not None else 0.
        self.output = Queue(maxsize=2)
        self.errors = Queue()
        if state is not None:
            self._publish(0)
        self.thread = Thread(target=self._run, name="n-body-simulation", daemon=True)
        self.thread.start()

    def configure(self, *, paused=None, rate=None, dt=None):
        if dt is not None and (not np.isfinite(dt) or dt <= 0):
            raise ValueError("Timestep must be positive and finite.")
        if rate is not None and (not np.isfinite(rate) or rate <= 0):
            raise ValueError("Playback rate must be positive and finite.")
        with self.condition:
            if paused is not None:
                self.paused = paused or self.state is None
            if rate is not None:
                self.rate = rate
            if dt is not None:
                self.dt = dt
            self.budget.debt = 0
            self.condition.notify()

    def single_step(self):
        with self.condition:
            if self.state is None:
                return
            self.paused = True
            self.single_steps = min(self.single_steps + 1, 10)
            self.condition.notify()

    def reset(self, state):
        with self.condition:
            self.state = state.copy()
            self.generation += 1
            self.budget.debt = 0
            self.single_steps = 0
            self.history.clear()
            self.history.append(self.state.positions.copy())
            self.last_sample = state.elapsed
            self._publish(0)
            self.condition.notify()
            return self.generation

    def latest(self):
        result = None
        while True:
            try:
                result = self.output.get_nowait()
            except Empty:
                return result

    def close(self):
        with self.condition:
            self.stopping = True
            self.condition.notify()
        self.thread.join(timeout=3)

    def _publish(self, achieved_rate):
        snap = Snapshot(self.generation, self.state.elapsed, readonly(self.state.positions),
                        readonly(self.state.velocities), readonly(self.history),
                        monotonic(), achieved_rate)
        if self.output.full():
            try:
                self.output.get_nowait()
            except Empty:
                pass
        self.output.put_nowait(snap)

    def _run(self):
        previous = monotonic()
        while True:
            with self.condition:
                self.condition.wait(timeout=0.016)
                now = monotonic()
                wall = now - previous
                previous = now
                if self.stopping:
                    return
                count = self.single_steps if self.paused else self.budget.consume(
                    wall, self.rate, self.dt)
                self.single_steps = 0
                if self.state is None or not count:
                    continue
                started = monotonic()
                try:
                    for _ in range(count):
                        step(self.state, self.dt)
                        if self.state.elapsed - self.last_sample >= 86400:
                            self.history.append(self.state.positions.copy())
                            self.last_sample = self.state.elapsed
                    achieved = count * self.dt / max(wall, monotonic() - started, 1e-6)
                    self._publish(achieved)
                except (ValueError, FloatingPointError) as exc:
                    self.paused = True
                    self.errors.put(str(exc))
