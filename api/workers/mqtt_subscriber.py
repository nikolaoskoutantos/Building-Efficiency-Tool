import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

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


def extract_device_key(topic: str) -> Optional[str]:
    parts = topic.split("/")
    for i, part in enumerate(parts):
        if part == "device" and i + 1 < len(parts):
            return parts[i + 1]
    return None


def extract_by_path(payload: dict, path: str):
    keys = path.split(".")
    value = payload
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC, qos=1)
        logger.info("Subscribed to topic: %s", MQTT_TOPIC)
    else:
        logger.error("Failed to connect, rc=%s", rc)


def on_message(client, userdata, msg):
    ts = datetime.now(timezone.utc)

    device_key = extract_device_key(msg.topic)
    if not device_key:
        logger.warning("Could not extract device_key from topic: %s", msg.topic)
        return

    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception as e:
        logger.warning("Invalid JSON payload topic=%s err=%s", msg.topic, e)
        return

    db = SessionLocal()
    inserted = 0

    try:
        sensors = (
            db.query(Sensor)
            .filter(Sensor.device_key == device_key)
            .all()
        )

        if not sensors:
            logger.warning("No sensors configured for device_key=%s", device_key)
            return

        for sensor in sensors:
            raw_value = extract_by_path(payload, sensor.payload_path)
            if raw_value is None:
                continue

            try:
                value = float(raw_value)
            except Exception:
                logger.warning(
                    "Invalid value for sensor_id=%s path=%s raw=%s",
                    sensor.id, sensor.payload_path, raw_value
                )
                continue

            db.add(SensorDataRaw(
                sensor_id=sensor.id,
                timestamp=ts,
                value=value,
                measurement_type=sensor.type,
                unit=sensor.unit,
                payload=payload,
            ))

            inserted += 1

        if inserted > 0:
            db.commit()
            logger.info(
                "Inserted %s rows for device_key=%s",
                inserted, device_key
            )
        else:
            db.rollback()

    except Exception as e:
        db.rollback()
        logger.error(
            "DB insert error topic=%s device_key=%s err=%s",
            msg.topic, device_key, e
        )
    finally:
        db.close()


def main():

    # Print MQTT connection info for debugging
    print("MQTT Connection Info:")
    print(f"  Host: {MQTT_HOST}")
    print(f"  Port: {MQTT_PORT}")
    print(f"  User: {MQTT_USER}")
    print(f"  Topic: {MQTT_TOPIC}")
    print(f"  Client ID: {MQTT_CLIENT_ID}")

    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    client.on_connect = on_connect
    client.on_message = on_message

    client.reconnect_delay_set(min_delay=1, max_delay=30)

    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()