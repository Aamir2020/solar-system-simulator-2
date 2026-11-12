from dataclasses import dataclass
from datetime import datetime, timedelta
from importlib.resources import files
import json
from .catalog import BODIES
from ..physics.system import State


@dataclass
class Scenario:
    state: State
    epoch: str
    source: str
    frame: str = "ICRF / ecliptic J2000 · solar-system barycenter · 2D projection"

    def date_at(self, seconds):
        epoch = datetime.fromisoformat(self.epoch)
        try:
            return (epoch + timedelta(seconds=seconds)).strftime("%Y-%m-%d %H:%M") + " TDB"
        except OverflowError:
            return f"Epoch + {seconds / 86400:,.0f} days TDB"


def demo_scenario():
    data = json.loads(files("solar_system_simulator").joinpath("assets/demo.json").read_text())
    if data['names'] != [b.name for b in BODIES]:
        raise ValueError("Bundled scenario catalog does not match.")
    state = State(data['positions_m'], data['velocities_m_s'], [b.mass for b in BODIES])
    return Scenario(state, data['epoch_tdb'], data['source'])
