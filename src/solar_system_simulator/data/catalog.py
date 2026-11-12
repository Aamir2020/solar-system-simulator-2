"""Masses preserve the original simulator; radii are approximate visual metadata."""
from dataclasses import dataclass

AU = 149_597_870_700.0
DAY = 86_400.0


@dataclass(frozen=True)
class Body:
    name: str
    horizons_id: int
    mass: float
    radius: float
    color: str


BODIES = (
    Body("Sun", 10, 1.989e30, 696_340_000, "#ffd393"),
    Body("Mercury", 199, 3.302e23, 2_439_700, "#b0a89e"),
    Body("Venus", 299, 4.869e24, 6_051_800, "#dfbd83"),
    Body("Earth", 399, 5.972e24, 6_371_000, "#63bad4"),
    Body("Mars", 499, 6.417e23, 3_389_500, "#d38464"),
    Body("Jupiter", 599, 1.898e27, 69_911_000, "#d4b293"),
    Body("Saturn", 699, 5.683e26, 58_232_000, "#e4ce99"),
    Body("Uranus", 799, 8.681e25, 25_362_000, "#9cdae0"),
    Body("Neptune", 899, 1.04e26, 24_622_000, "#688de1"),
)
