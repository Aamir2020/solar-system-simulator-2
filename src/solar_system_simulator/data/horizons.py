"""Serial Horizons vector loading with explicit conventions and validated disk caching."""
import csv
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import Event
import tempfile

import numpy as np
import requests

from .catalog import BODIES
from .scenario import Scenario
from ..physics.system import State

URL = "https://ssd.jpl.nasa.gov/api/horizons.api"


class HorizonsError(RuntimeError):
    pass


class Cancelled(HorizonsError):
    pass


def normalize_epoch(value):
    try:
        epoch = datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise HorizonsError("Use a TDB calendar date such as 2026-01-01 00:00:00.") from exc
    if epoch.tzinfo is not None or not 1900 <= epoch.year <= 2100:
        raise HorizonsError("Choose a TDB date from 1900 through 2100 without a timezone suffix.")
    return epoch.replace(microsecond=0).isoformat(timespec="seconds")


def parameters(body_id, epoch):
    instant = datetime.fromisoformat(normalize_epoch(epoch))
    jd = 2451545.0 + (instant - datetime(2000, 1, 1, 12)).total_seconds() / 86400
    return {
        "format": "json", "COMMAND": str(body_id), "OBJ_DATA": "NO", "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS", "CENTER": "500@0", "TLIST": f"{jd:.10f}",
        "TLIST_TYPE": "JD", "TIME_TYPE": "TDB", "OUT_UNITS": "KM-S",
        "REF_SYSTEM": "ICRF", "REF_PLANE": "ECLIPTIC", "VEC_CORR": "NONE",
        "VEC_TABLE": "2", "CSV_FORMAT": "YES",
    }


def parse_vectors(payload, expected_jd=None):
    if not isinstance(payload, dict):
        raise HorizonsError("NASA returned an unexpected response type.")
    if payload.get("error"):
        raise HorizonsError(f"NASA Horizons: {str(payload['error'])[:400]}")
    signature = payload.get("signature", {})
    if not isinstance(signature, dict) or not signature.get("version"):
        raise HorizonsError("NASA response is missing API provenance.")
    result = payload.get("result")
    if not isinstance(result, str) or "$$SOE" not in result or "$$EOE" not in result:
        raise HorizonsError("NASA response did not contain a vector table.")
    table = result.split("$$SOE", 1)[1].split("$$EOE", 1)[0].strip()
    rows = list(csv.reader(line for line in table.splitlines() if line.strip()))
    if len(rows) != 1 or len(rows[0]) < 8:
        raise HorizonsError("Expected exactly one complete NASA vector row.")
    row = rows[0]
    try:
        jd = float(row[0])
        values = np.array([float(v.replace("D", "E")) for v in row[2:8]], dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise HorizonsError("NASA vector table contained invalid numbers.") from exc
    if not np.isfinite(jd) or not np.isfinite(values).all():
        raise HorizonsError("NASA vector table contained non-finite numbers.")
    if expected_jd is not None and abs(jd - expected_jd) > 1e-7:
        raise HorizonsError("NASA returned vectors for a different epoch.")
    return values[:2] * 1000, values[3:5] * 1000


class HorizonsClient:
    def __init__(self, cache_directory, session=None, retries=2):
        self.cache = Path(cache_directory)
        self.session = session or requests.Session()
        self.retries = retries

    def _load(self, params, cancel):
        key = sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        path = self.cache / f"{key}.json"
        if path.exists():
            try:
                cached = json.loads(path.read_text())
                if cached["request"] == params:
                    parse_vectors(cached["response"], float(params['TLIST']))
                    return cached['response']
            except (OSError, ValueError, KeyError, HorizonsError):
                pass  # A corrupt or incompatible cache must never change the requested date.
        for attempt in range(self.retries + 1):
            if cancel.is_set():
                raise Cancelled("NASA loading cancelled.")
            try:
                response = self.session.get(URL, params=params, timeout=(5, 15))
                response.raise_for_status()
                payload = response.json()
                parse_vectors(payload, float(params['TLIST']))
                if cancel.is_set():
                    raise Cancelled("NASA loading cancelled.")
                self._store(path, {"request": params, "response": payload})
                return payload
            except requests.RequestException as exc:
                if attempt == self.retries:
                    raise HorizonsError(f"Unable to load NASA data: {exc}") from exc
                if cancel.wait(0.5 * 2 ** attempt):
                    raise Cancelled("NASA loading cancelled.")
            except ValueError as exc:
                raise HorizonsError("NASA returned malformed JSON.") from exc
        raise HorizonsError("Unable to load NASA data.")

    def _store(self, path, payload):
        # Caching is optional; a read-only/full disk must not discard a valid NASA response.
        temporary = None
        try:
            self.cache.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', dir=self.cache, delete=False) as out:
                temporary = out.name
                json.dump(payload, out)
            os.replace(temporary, path)
        except OSError:
            if temporary:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass

    def load(self, epoch, progress=None, cancel=None):
        epoch = normalize_epoch(epoch)
        cancel = cancel or Event()
        positions, velocities, versions = [], [], set()
        try:
            for i, body in enumerate(BODIES):
                if cancel.is_set():
                    raise Cancelled("NASA loading cancelled.")
                if progress:
                    progress(i, f"Loading {body.name} ({i + 1}/{len(BODIES)})…")
                params = parameters(body.horizons_id, epoch)
                payload = self._load(params, cancel)
                position, velocity = parse_vectors(payload, float(params['TLIST']))
                positions.append(position)
                velocities.append(velocity)
                versions.add(str(payload['signature']['version']))
            state = State(positions, velocities, [b.mass for b in BODIES])
            return Scenario(state, epoch, "NASA/JPL Horizons · API " + ", ".join(sorted(versions)))
        finally:
            self.session.close()
