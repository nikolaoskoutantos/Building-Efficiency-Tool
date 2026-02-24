import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from models.sensordata import SensorDataRaw
from models.sensor import Sensor

load_dotenv()

MQTT_HOST = os.environ["MQTT_HOST"]
MQTT_PORT = int(os.environ["MQTT_PORT"])
MQTT_USER = os.environ.get("MQTT_USER")
MQTT_PASS = os.environ.get("MQTT_PASS")
MQTT_TOPIC = os.environ["MQTT_TOPIC"]
MQTT_CLIENT_ID = os.environ["MQTT_CLIENT_ID"]
DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mqtt_subscriber")

sensor_id_cache: Dict[Tuple[str, str], int] = {}

def resolve_sensor_id(db, device_key: str, measurement_type: str) -> Optional[int]:
    key = (device_key, measurement_type)
    cached = sensor_id_cache.get(key)
    if cached:
        return cached

    sensor = (
        db.query(Sensor)
        .filter(Sensor.device_key == device_key, Sensor.type == measurement_type)
        .first()
    )
    if sensor:
        sensor_id_cache[key] = sensor.id
        return sensor.id

    logger.warning("Sensor not found: device_key=%s type=%s", device_key, measurement_type)
    return None

def extract_metrics(payload: dict):
    metrics = []
    if "apower" in payload:
        metrics.append(("apower_w", float(payload["apower"]), "watt"))
    if "voltage" in payload:
        metrics.append(("voltage_v", float(payload["voltage"]), "volt"))
    if "current" in payload:
        metrics.append(("current_a", float(payload["current"]), "ampere"))
    if "total" in payload:
        metrics.append(("energy_wh", float(payload["total"]), "watt_hour"))
    return metrics

def extract_device_key(topic: str) -> Optional[str]:
    parts = topic.split("/")
    for i, part in enumerate(parts):
        if part == "device" and i + 1 < len(parts):
            return parts[i + 1]
    return None

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC, qos=1)
        logger.info("Subscribed to topic: %s", MQTT_TOPIC)
    else:
        logger.error("Failed to connect, rc=%s", rc)

    ts = datetime.now(timezone.utc)  # timezone-aware UTC for DB consistency
    device_key = extract_device_key(msg.topic)
    if not device_key:
        logger.warning("Could not extract device_key from topic: %s", msg.topic)
        return

    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception as e:
        logger.warning("Invalid JSON payload topic=%s err=%s", msg.topic, e)
        return

    metrics = extract_metrics(payload)
    if not metrics:
        return

    inserted = 0
    db = SessionLocal()
    try:
        for measurement_type, value, unit in metrics:
            sensor_id = resolve_sensor_id(db, device_key, measurement_type)
            if not sensor_id:
                continue

            db.add(SensorDataRaw(
                sensor_id=sensor_id,
                timestamp=ts,
                value=value,
                measurement_type=measurement_type,
                unit=unit,
                payload=payload,
            ))
            inserted += 1

        if inserted:
            db.commit()
            logger.info("Inserted %s rows for device_key=%s", inserted, device_key)
        else:
            db.rollback()
    except Exception as e:
        db.rollback()
        logger.error("DB insert error topic=%s device_key=%s err=%s", msg.topic, device_key, e)
    finally:
        db.close()

def main():
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    client.on_connect = on_connect
    client.on_message = on_message

    # basic resiliency
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_forever()

if __name__ == "__main__":
    main()