"""
Unit resolver — normalises any raw unit string to a canonical SensorUnit row.

Usage:
    from utils.unit_resolver import resolve_unit
    unit_row = resolve_unit("celsius", db)
    # → SensorUnit(symbol="°C", quantity="temperature", …)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from models.sensor_unit import SensorUnit as SensorUnitType


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalise(raw: str) -> str:
    """Lowercase, strip, collapse whitespace, drop common noise chars."""
    s = raw.strip().lower()
    s = re.sub(r"[\s_-]+", "_", s)   # spaces/hyphens/underscores → single _
    s = s.rstrip("_")
    return s


# Cheap pre-normalisation map applied before DB lookup.
# Maps common alternate forms → the canonical symbol so the DB index is hit first.
_SYMBOL_QUICK_MAP: dict[str, str] = {
    # temperature
    "celsius": "°C",
    "degc": "°C",
    "deg_c": "°C",
    "degree_celsius": "°C",
    "degrees_celsius": "°C",
    "fahrenheit": "°F",
    "degf": "°F",
    "deg_f": "°F",
    "degree_fahrenheit": "°F",
    "kelvin": "K",
    # humidity / ratio
    "%rh": "%",
    "pct": "%",
    "percent": "%",
    "humidity_pct": "%",
    # power
    "watt": "W",
    "watts": "W",
    "kilowatt": "kW",
    "kilowatts": "kW",
    # energy
    "kwh": "kWh",
    "kilowatt_hour": "kWh",
    "kilowatt_hours": "kWh",
    "kilowatthour": "kWh",
    "wh": "Wh",
    "watt_hour": "Wh",
    "watthour": "Wh",
    # current
    "ampere": "A",
    "amp": "A",
    "amps": "A",
    "amperes": "A",
    # voltage
    "volt": "V",
    "volts": "V",
    # concentration
    "parts_per_million": "ppm",
    "co2_ppm": "ppm",
    # pressure
    "hpa": "hPa",
    "hectopascal": "hPa",
    "mbar": "hPa",
    "millibar": "hPa",
    "mb": "hPa",
    "pascal": "Pa",
    "pa": "Pa",
    # speed
    "m_s": "m/s",
    "ms": "m/s",
    "meters_per_second": "m/s",
    "metres_per_second": "m/s",
    "meter_per_second": "m/s",
    # length / precipitation
    "millimeter": "mm",
    "millimetre": "mm",
    "millimeters": "mm",
    "millimetres": "mm",
    # boolean
    "boolean": "bool",
    "on_off": "bool",
    "binary": "bool",
    "true_false": "bool",
    # illuminance
    "lux": "lx",
    # sound
    "decibel": "dB",
    "decibels": "dB",
}


def canonicalize_unit(raw: str, db) -> tuple[Optional[str], Optional[int]]:
    """Return (canonical_symbol, unit_id) for a raw unit string.

    If the unit is unknown, the raw trimmed string is preserved and unit_id is
    returned as None so callers can keep backward-compatible writes while still
    using the canonical unit registry whenever possible.
    """
    if not raw:
        return None, None

    unit_row = resolve_unit(raw, db)
    if unit_row:
        return unit_row.symbol, unit_row.id
    return raw.strip(), None


def resolve_unit(raw: str, db) -> "Optional[SensorUnitType]":
    """
    Return the canonical SensorUnit for *raw*, or None if unrecognised.

    Resolution order:
      1. Quick in-process map → canonical symbol string → exact DB symbol lookup
      2. Case-insensitive DB symbol match
      3. JSONB aliases array scan (DB-side)

    Returns None (never raises) if the sensor_units table does not yet exist
    (e.g. called before the migration that creates it).
    """
    from models.sensor_unit import SensorUnit  # local import to avoid circular deps
    from sqlalchemy.exc import ProgrammingError, OperationalError

    if not raw:
        return None

    try:
        normalised = _normalise(raw)
        candidate_symbol = _SYMBOL_QUICK_MAP.get(normalised, raw.strip())

        # 1. Exact symbol match (covers canonical symbols passed directly, e.g. "°C")
        unit = (
            db.query(SensorUnit)
            .filter(SensorUnit.symbol == candidate_symbol)
            .first()
        )
        if unit:
            return unit

        # 2. Case-insensitive symbol match (handles "w" → "W", "kwh" → "kWh" etc.)
        from sqlalchemy import func as sqlfunc
        unit = (
            db.query(SensorUnit)
            .filter(sqlfunc.lower(SensorUnit.symbol) == normalised)
            .first()
        )
        if unit:
            return unit

        # 3. Alias scan — PostgreSQL JSONB @> operator checks if array contains value
        unit = (
            db.query(SensorUnit)
            .filter(SensorUnit.aliases.contains([normalised]))
            .first()
        )
        return unit

    except (ProgrammingError, OperationalError):
        # Table doesn't exist yet (pre-migration). Graceful degradation.
        db.rollback()
        return None
