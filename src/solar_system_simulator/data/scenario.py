from dataclasses import dataclass
from datetime import datetime, timedelta
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
