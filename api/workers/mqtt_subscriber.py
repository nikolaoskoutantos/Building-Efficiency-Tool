import os
import json
import logging
import queue
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import paho.mqtt.client as mqtt
import yaml
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

from db.connection import SessionLocal
from models.sensordata import SensorDataRaw
from models.sensor import Sensor
from models.hvac_unit import HVACUnit
from models.device_command import DeviceCommand
from workers.payload_extractor import PayloadExtractor

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mqtt_subscriber")

# ---------------------------------------------------------------------------
# Topic routing — loaded from topic_routing.yaml next to this file.
# Keys: heartbeat, command  →  sets of second-segment values.
# Anything not matched defaults to sensor data extraction.
# ---------------------------------------------------------------------------
_ROUTING_FILE = Path(__file__).parent / "topic_routing.yaml"

def _load_routing() -> dict:
    try:
        with open(_ROUTING_FILE) as f:
            cfg = yaml.safe_load(f)
        routing = cfg.get("routing", {})
        return {
            "heartbeat": set(routing.get("heartbeat", [])),
            "command":   set(routing.get("command",   [])),
        }
    except Exception as e:
        logger.warning("Could not load topic_routing.yaml, using defaults: %s", e)
        return {"heartbeat": {"status"}, "command": {"cmd", "command"}}

_ROUTING = _load_routing()

# ---------------------------------------------------------------------------
# Message queue — decouples paho network thread from DB work.
# on_message enqueues raw bytes instantly; drain workers do the heavy lifting.
# maxsize caps memory under extreme burst load; excess messages are dropped
# with a warning rather than blocking the paho thread.
# ---------------------------------------------------------------------------
_msg_queue: queue.Queue = queue.Queue(maxsize=10_000)


def extract_device_key(topic: str) -> Optional[str]:
    """Topic format: {device_key}/...  — device_key is always the first segment."""
    parts = topic.split("/")
    return parts[0] if parts and parts[0] else None


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT broker")
        topic = os.environ.get("MQTT_TOPIC", "building/#")
        client.subscribe(topic, qos=1)
        logger.info("Subscribed to topic: %s", topic)
    else:
        logger.error("Failed to connect, rc=%s", rc)


def _touch_device(hvac_unit: HVACUnit, ts: datetime, status: str = "online") -> None:
    """Update last_seen_at and connection_status in place (caller must commit)."""
    hvac_unit.last_seen_at = ts
    hvac_unit.connection_status = status


# ---------------------------------------------------------------------------
# Per-resource handlers
# ---------------------------------------------------------------------------

def handle_sensor_direct(
    db, hvac_unit: HVACUnit, sensor_id: int, payload, ts: datetime
) -> None:
    """Write a single value to the sensor identified by sensor_id in the topic.

    Payload can be a bare JSON number (e.g. 250.5) or {"value": 250.5}.
    The sensor must belong to this hvac_unit — mismatches are silently dropped.
    """
    sensor = (
        db.query(Sensor)
        .filter(Sensor.id == sensor_id, Sensor.hvac_unit_id == hvac_unit.id)
        .first()
    )
    if not sensor:
        logger.warning(
            "sensor_id=%s not found or not owned by device_key=%s",
            sensor_id, hvac_unit.device_key,
        )
        return

    # Accept: bare scalar (250.5), {"value": 250.5}, or any vendor JSON (Shelly, etc.)
    # Priority: scalar → {"value": X} → payload_path extraction on the sensor record
    if isinstance(payload, (int, float)):
        raw_value = float(payload)
        payload_dict: dict = {"value": raw_value}
    elif isinstance(payload, dict):
        if "value" in payload:
            raw_value = payload["value"]
        elif sensor.payload_path:
            raw_value = PayloadExtractor.extract(payload, sensor.payload_path)
        else:
            logger.warning(
                "No 'value' key and no payload_path for sensor_id=%s", sensor_id
            )
            return
        payload_dict = payload
    else:
        logger.warning("Unsupported payload type for sensor_direct sensor_id=%s", sensor_id)
        return

    if raw_value is None:
        logger.warning(
            "Could not extract value for sensor_id=%s payload_path=%s",
            sensor_id, sensor.payload_path,
        )
        return

    row = SensorDataRaw(
        sensor_id=sensor.id,
        building_id=hvac_unit.building_id,
        ts=ts,
        value=float(raw_value),
        payload=payload_dict,
        msg_id=payload_dict.get("msg_id"),
    )
    db.add(row)
    logger.info("Direct sensor write sensor_id=%s value=%s", sensor_id, raw_value)


def handle_sensor(db, hvac_unit: HVACUnit, payload: dict, ts: datetime) -> None:
    """Map JSON payload to sensor rows and write to sensor_data_raw."""
    sensors = (
        db.query(Sensor)
        .filter(Sensor.hvac_unit_id == hvac_unit.id)
        .all()
    )

    if not sensors:
        logger.warning("No sensors configured for device_key=%s", hvac_unit.device_key)
        return

    inserted = 0
    for sensor in sensors:
        row = _parse_sensor_row(sensor, hvac_unit, payload, ts)
        if row is not None:
            db.add(row)
            inserted += 1

    if inserted:
        logger.info("Sensor rows queued=%s device_key=%s", inserted, hvac_unit.device_key)


def _parse_sensor_row(
    sensor: Sensor, hvac_unit: HVACUnit, payload: dict, ts: datetime
) -> Optional[SensorDataRaw]:
    if not sensor.payload_path:
        return None
    raw_value = PayloadExtractor.extract(payload, sensor.payload_path)
    if raw_value is None:
        return None

    num_value = text_value = bool_value = None
    if isinstance(raw_value, bool):
        bool_value = raw_value
    elif isinstance(raw_value, str):
        try:
            num_value = float(raw_value)
        except ValueError:
            text_value = raw_value
    else:
        try:
            num_value = float(raw_value)
        except Exception:
            logger.warning(
                "Unhandled value sensor_id=%s path=%s raw=%s",
                sensor.id, sensor.payload_path, raw_value,
            )
            return None

    return SensorDataRaw(
        sensor_id=sensor.id,
        building_id=hvac_unit.building_id,
        ts=ts,
        value=num_value,
        value_text=text_value,
        value_bool=bool_value,
        payload=payload,
        msg_id=payload.get("msg_id"),  # optional device-supplied dedup UUID
    )


def handle_status(hvac_unit: HVACUnit, payload: dict, ts: datetime) -> None:
    """
    Device status heartbeat / online-offline signal.
    Expected payload: { "status": "online" | "offline", ... }
    Falls back to "online" when the field is absent.
    """
    reported = payload.get("status", "online")
    _touch_device(hvac_unit, ts, reported)
    logger.info(
        "Status update device_key=%s status=%s", hvac_unit.device_key, reported
    )


def handle_cmd_ack(db, hvac_unit: HVACUnit, payload: dict, ts: datetime) -> None:
    """
    Device acknowledges a command.
    Expected payload: { "command_id": <int>, "status": "acked" | "failed", ... }
    Updates device_commands.acked_at and status.
    """
    command_id = payload.get("command_id")
    if command_id is None:
        logger.warning(
            "cmd ACK without command_id device_key=%s payload=%s",
            hvac_unit.device_key, payload,
        )
        return

    cmd = (
        db.query(DeviceCommand)
        .filter(
            DeviceCommand.id == int(command_id),
            DeviceCommand.hvac_unit_id == hvac_unit.id,
        )
        .first()
    )
    if not cmd:
        logger.warning(
            "cmd ACK for unknown command_id=%s device_key=%s",
            command_id, hvac_unit.device_key,
        )
        return

    ack_status = payload.get("status", "acked")
    cmd.acked_at = ts
    cmd.status = ack_status
    logger.info(
        "cmd ACK command_id=%s status=%s device_key=%s",
        command_id, ack_status, hvac_unit.device_key,
    )


# ---------------------------------------------------------------------------
# Main message dispatcher — two layers
# ---------------------------------------------------------------------------

def on_message(client, userdata, msg):
    """Called by paho network thread. Must return instantly — just enqueue."""
    ts = datetime.now(timezone.utc)
    try:
        _msg_queue.put_nowait((msg.topic, msg.payload, ts))
    except queue.Full:
        logger.warning(
            "Message queue full (size=%d), dropping topic=%s",
            _msg_queue.qsize(), msg.topic,
        )


def _is_timestamp_fresh(ts: datetime) -> bool:
    """Return True if ts is within the acceptable window.

    Rejects:
    - Messages older than 10 minutes (stale / replay)
    - Messages with a future timestamp > 2 minutes (clock skew / tampering)
    """
    now = datetime.now(timezone.utc)
    age = now - ts
    return timedelta(minutes=-2) <= age <= timedelta(minutes=10)


def _resolve_resource(parts: list[str]) -> tuple[str, str]:
    """Classify topic into a logical resource and return (resource, second_segment)."""
    # UUID-based routing: the device_key (first segment) identifies the device.
    # The rest of the topic is vendor-specific and handled by payload_path.
    # Routing rules are loaded from topic_routing.yaml — no code change needed
    # when adding a new vendor or topic format.
    second = parts[1] if len(parts) >= 2 else ""

    if second in _ROUTING["heartbeat"] and len(parts) == 2:
        return "status", second      # pure heartbeat — 2-segment only
    if second in _ROUTING["command"]:
        return "cmd", second
    if second.isdigit():
        return "sensor_direct", second   # {device_key}/{sensor_id} — direct single-sensor write
    return "sensor", second              # default: payload_path extraction (Shelly, KNX, etc.)


def _decode_payload(topic: str, payload_bytes: bytes):
    try:
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        logger.warning("Invalid JSON payload topic=%s err=%s", topic, e)
        return None


def _load_active_hvac_unit(db, device_key: str) -> Optional[HVACUnit]:
    hvac_unit = (
        db.query(HVACUnit)
        .filter(HVACUnit.device_key == device_key)
        .first()
    )
    if not hvac_unit:
        logger.warning("No HVACUnit found for device_key=%s", device_key)
        return None
    if hvac_unit.device_revoked_at:
        logger.warning(
            "Dropping message from revoked device device_key=%s", device_key
        )
        return None
    return hvac_unit


def _persist_last_seen_only(db, hvac_unit: HVACUnit, ts: datetime, device_key: str) -> bool:
    _touch_device(hvac_unit, ts)
    if _is_timestamp_fresh(ts):
        return True
    logger.warning(
        "Dropping stale/future MQTT message device_key=%s ts=%s",
        device_key, ts.isoformat(),
    )
    db.commit()  # persist the last_seen update only
    return False


def _handle_duplicate_message(db, device_key: str, topic: str) -> None:
    db.rollback()
    logger.warning(
        "Duplicate MQTT msg_id rejected device_key=%s topic=%s",
        device_key, topic,
    )


def _dispatch_resource(db, hvac_unit: HVACUnit, resource: str, second: str, payload, ts: datetime) -> None:
    if resource == "status":
        handle_status(hvac_unit, payload, ts)
        return
    if resource == "cmd":
        handle_cmd_ack(db, hvac_unit, payload, ts)
        return
    if resource == "sensor_direct":
        handle_sensor_direct(db, hvac_unit, int(second), payload, ts)
        return
    handle_sensor(db, hvac_unit, payload, ts)


def _process_message(topic: str, payload_bytes: bytes, ts: datetime) -> None:
    """Heavy path — runs in a drain worker thread, does all DB work."""
    device_key = extract_device_key(topic)
    if not device_key:
        logger.warning("Could not extract device_key from topic: %s", topic)
        return

    parts = topic.split("/")
    resource, second = _resolve_resource(parts)

    payload = _decode_payload(topic, payload_bytes)
    if payload is None:
        return

    db = SessionLocal()
    try:
        hvac_unit = _load_active_hvac_unit(db, device_key)
        if not hvac_unit:
            return

        if not _persist_last_seen_only(db, hvac_unit, ts, device_key):
            return

        _dispatch_resource(db, hvac_unit, resource, second, payload, ts)
        db.commit()
    except IntegrityError:
        # Duplicate (sensor_id, msg_id) — this is a replayed message.
        _handle_duplicate_message(db, device_key, topic)
    except Exception:
        db.rollback()
        logger.exception("DB error topic=%s device_key=%s", topic, device_key)
    finally:
        db.close()


def _drain_worker() -> None:
    """Worker thread: pop from queue and process until the process exits."""
    logger.info("MQTT drain worker started thread=%s", threading.current_thread().name)
    while True:
        try:
            topic, payload_bytes, ts = _msg_queue.get(timeout=1)
        except queue.Empty:
            continue
        try:
            _process_message(topic, payload_bytes, ts)
        except Exception:
            logger.exception("Unhandled error in drain worker")
        finally:
            _msg_queue.task_done()


def start_subscriber(num_workers: int = 2) -> mqtt.Client:
    """
    Start the MQTT subscriber and DB drain workers as daemon threads.
    Safe to call from FastAPI lifespan — does not block.
    num_workers controls DB concurrency; 2 is a safe default, raise to 4-8
    under heavy sensor load (each worker holds one SQLAlchemy connection).

    Env vars are read here (not at module import time) so that importing this
    module never crashes the API when MQTT is not configured.
    """
    mqtt_host = os.environ["MQTT_HOST"]
    mqtt_port = int(os.environ["MQTT_PORT"])
    mqtt_user = os.environ.get("MQTT_USER")
    mqtt_pass = os.environ.get("MQTT_PASS")
    mqtt_topic = os.environ["MQTT_TOPIC"]
    mqtt_client_id = os.environ["MQTT_CLIENT_ID"]

    # Start drain workers first so the queue is always drained
    for i in range(num_workers):
        t = threading.Thread(
            target=_drain_worker,
            daemon=True,
            name=f"mqtt-drain-{i}",
        )
        t.start()
    logger.info("Started %d MQTT drain worker(s)", num_workers)

    # Build and connect paho client
    client = mqtt.Client(client_id=mqtt_client_id)
    if mqtt_user:
        client.username_pw_set(mqtt_user, mqtt_pass)
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    try:
        client.connect(mqtt_host, mqtt_port, keepalive=60)
    except Exception as exc:
        logger.warning(
            "MQTT broker unavailable (%s:%s) — subscriber not started: %s",
            mqtt_host, mqtt_port, exc,
        )
        return None

    # loop_forever blocks — run it in its own daemon thread
    paho_thread = threading.Thread(
        target=client.loop_forever,
        daemon=True,
        name="mqtt-paho",
    )
    paho_thread.start()
    logger.info(
        "MQTT paho thread started host=%s port=%s topic=%s",
        mqtt_host, mqtt_port, mqtt_topic,
    )

    return client


def main():
    """Standalone entry point — starts subscriber and blocks until killed."""
    mqtt_host = os.environ["MQTT_HOST"]
    mqtt_port = int(os.environ["MQTT_PORT"])
    mqtt_user = os.environ.get("MQTT_USER")
    mqtt_topic = os.environ["MQTT_TOPIC"]
    mqtt_client_id = os.environ["MQTT_CLIENT_ID"]

    print("MQTT Connection Info:")
    print(f"  Host: {mqtt_host}")
    print(f"  Port: {mqtt_port}")
    print(f"  User: {mqtt_user}")
    print(f"  Topic: {mqtt_topic}")
    print(f"  Client ID: {mqtt_client_id}")

    num_workers = int(os.environ.get("MQTT_WORKER_THREADS", "2"))
    start_subscriber(num_workers=num_workers)

    # Block main thread forever (all workers are daemons)
    threading.Event().wait()


if __name__ == "__main__":
    main()
