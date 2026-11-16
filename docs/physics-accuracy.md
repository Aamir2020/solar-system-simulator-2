# Physics accuracy

The simulator uses direct, three-dimensional Newtonian gravity and fixed-step
kick–drift–kick leapfrog. NASA's X/Y/Z positions and velocities remain in the
physics state. The camera projects X/Y for the two-dimensional display.

## Choosing the default step

We compared one-day, six-hour, and one-hour steps over **1,825 days** (five
365-day years), starting on **2026-01-01 TDB**. All runs used the same Sun and
eight planets, local masses, and frozen NASA initial vectors. Positions and
conservation errors were sampled at the same daily times.

The position difference is the three-dimensional distance from a **15-minute
reference integration**, measured relative to the Sun. The largest sampled
differences occurred for Mercury.

| Physics step | Largest position difference | Largest relative energy error | Run time |
| --- | ---: | ---: | ---: |
| 1 day | 12,542,124 km | 2.65 × 10⁻⁶ | 0.43 s |
| 6 hours | 787,579 km | 1.68 × 10⁻⁷ | 0.76 s |
| **1 hour (default)** | **20,552 km** | **4.67 × 10⁻⁹** | **2.88 s** |

The one-hour step substantially reduces accumulated orbital position error and
is fast enough for the normal 30 simulated days per second on the benchmark
machine. Six-hour and one-day steps remain available for higher playback rates.
The physics step stays fixed as playback speed changes.

These results measure numerical convergence **within this model**, not agreement
with NASA's future ephemerides. The reference also has numerical error: a
30-minute run differed from the 15-minute run by up to 4,111 km. Energy conservation
alone does not guarantee correct orbital phase. Local masses are unchanged, and
moons, relativity, and other omitted forces also affect real-world accuracy.

Run times include daily diagnostics and vary by computer. These measurements used
CPython 3.10 and NumPy 2 on Linux x64. The [full report](physics-benchmark.json)
contains per-body differences, momentum checks, and reference diagnostics.

## Reproduce the checks

After installing from source, run:

```bash
python scripts/benchmark_physics.py --years 5 --output physics-benchmark.json
python -m unittest discover -s tests -v
```

The benchmark uses the original NASA API responses in
[the test fixture](../tests/fixtures/nasa_horizons_2026-01-01.json), including the
request settings and API provenance. It requires no network and supplies no
offline data to the application.

Automated tests also check an inclined eccentric two-body orbit against the
analytic Kepler solution, bounded energy error across ten orbits, three-year
nine-body convergence, conservation of linear and angular momentum, and the
original planar solver's trajectory embedded in 3D. Desktop checks cover loading,
selection, following, labels, zoom, and trail rendering with 3D state.
