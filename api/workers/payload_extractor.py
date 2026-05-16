"""
Payload extractor — strategy chain for reading sensor values from MQTT payloads.

Strategies are tried in order; the first one that returns a non-None value wins.
This makes the system vendor-agnostic: the DB payload_path tells the extractor
WHERE to look; each strategy handles a different payload encoding.

Supported payload_path formats:
  $.aenergy.total        JSONPath  (requires jsonpath-ng)
  $.sensors[0].temp      JSONPath with array index
  aenergy.total          Legacy dot-notation (backwards-compatible)
  temperature            Single key (legacy)
  $                      Whole payload as a scalar (ESPHome, HA state topics)
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger("mqtt_subscriber")

try:
    from jsonpath_ng import parse as _jsonpath_parse
    _JSONPATH_AVAILABLE = True
except ImportError:
    _JSONPATH_AVAILABLE = False
    logger.warning(
        "jsonpath-ng not installed — JSONPath paths (starting with '$') will be skipped. "
        "Install with: pip install jsonpath-ng"
    )


class PayloadExtractor:
    """
    Tries each registered strategy in order.
    First strategy that returns a non-None value wins.
    """

    _strategies: list = []

    @classmethod
    def strategy(cls, fn):
        """Decorator to register a strategy function."""
        cls._strategies.append(fn)
        return fn

    @classmethod
    def extract(cls, payload: Any, path: str) -> Optional[Any]:
        """
        Try all strategies against payload + path.
        Returns the first non-None result, or None if nothing matched.
        """
        for strategy in cls._strategies:
            try:
                result = strategy(payload, path)
                if result is not None:
                    return result
            except Exception:
                continue
        return None


# ── Strategy 1: JSONPath on dict payload ──────────────────────────────────────
@PayloadExtractor.strategy
def _jsonpath_strategy(payload: Any, path: str) -> Optional[Any]:
    """Handles paths starting with '$'. Requires jsonpath-ng."""
    if not isinstance(path, str) or not path.startswith("$"):
        return None
    if not _JSONPATH_AVAILABLE:
        return None
    if not isinstance(payload, dict):
        return None
    expr = _jsonpath_parse(path)
    matches = expr.find(payload)
    return matches[0].value if matches else None


# ── Strategy 2: Legacy dot-notation ──────────────────────────────────────────
@PayloadExtractor.strategy
def _dot_notation_strategy(payload: Any, path: str) -> Optional[Any]:
    """
    Traverses nested dicts using dot-separated keys.
    e.g. 'aenergy.total' → payload['aenergy']['total']
    Backwards-compatible with all existing DB payload_path values.
    """
    if not isinstance(path, str) or path.startswith("$") or not isinstance(payload, dict):
        return None
    value = payload
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


# ── Strategy 3: Whole-payload scalar fallback ─────────────────────────────────
@PayloadExtractor.strategy
def _scalar_fallback_strategy(payload: Any, path: str) -> Optional[Any]:
    """
    When path == '$', treat the entire payload as a scalar value.
    Useful for ESPHome, Home Assistant state topics, and any device
    that publishes a bare number or boolean as the message body.
    """
    if path != "$":
        return None
    if isinstance(payload, (int, float, bool)):
        return payload
    if isinstance(payload, str):
        stripped = payload.strip()
        for cast in (int, float):
            try:
                return cast(stripped)
            except ValueError:
                pass
        if stripped.lower() in ("true", "false"):
            return stripped.lower() == "true"
    return None
