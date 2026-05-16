from __future__ import annotations

import os
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from db.connection import engine

router = APIRouter()

DEFAULT_SOCKET_TIMEOUT_SECONDS = 2.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tcp_check(host: str | None, port: int | None, timeout: float = DEFAULT_SOCKET_TIMEOUT_SECONDS) -> bool:
    if not host or not port:
        return False

    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_uri_host_port(uri: str | None, default_port: int | None = None) -> tuple[str | None, int | None]:
    if not uri:
        return None, default_port

    parsed = urlparse(uri)
    return parsed.hostname, parsed.port or default_port


def _db_ready() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _dependency_status() -> dict[str, dict[str, object]]:
    mlflow_host, mlflow_port = _parse_uri_host_port(os.getenv("MLFLOW_TRACKING_URI"), 5000)
    mqtt_host = os.getenv("MQTT_HOST")
    mqtt_port_raw = os.getenv("MQTT_PORT", "1883")

    try:
        mqtt_port = int(mqtt_port_raw)
    except ValueError:
        mqtt_port = None

    deps = {
        "database": {"ok": _db_ready()},
        "mlflow": {
            "configured": bool(os.getenv("MLFLOW_TRACKING_URI")),
            "ok": _tcp_check(mlflow_host, mlflow_port) if mlflow_host else None,
        },
        "mqtt": {
            "configured": bool(mqtt_host),
            "ok": _tcp_check(mqtt_host, mqtt_port) if mqtt_host and mqtt_port else None,
        },
    }
    return deps


def _ready_payload() -> tuple[bool, dict[str, object]]:
    deps = _dependency_status()
    required_ok = bool(deps["database"]["ok"])
    optional_degraded = [
        name
        for name in ("mlflow", "mqtt")
        if deps[name]["configured"] and deps[name]["ok"] is False
    ]

    payload = {
        "status": "ready" if required_ok else "not_ready",
        "utc_timestamp": _utc_now_iso(),
        "checks": {
            "database": deps["database"]["ok"],
        },
        "degraded_dependencies": optional_degraded,
    }
    return required_ok, payload


@router.get("/health", tags=["Health"])
def health_summary(response: Response):
    ready, payload = _ready_payload()
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload


@router.get("/health/live", tags=["Health"])
def health_live():
    return {
        "status": "alive",
        "utc_timestamp": _utc_now_iso(),
    }


@router.get("/health/ready", tags=["Health"])
def health_ready(response: Response):
    ready, payload = _ready_payload()
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload


@router.get("/health/deps", tags=["Health"])
def health_deps(response: Response):
    deps = _dependency_status()
    database_ok = bool(deps["database"]["ok"])
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if database_ok else "degraded",
        "utc_timestamp": _utc_now_iso(),
        "dependencies": deps,
    }
