"""
Singleton MQTT publisher for backend-to-device control signals.

Used by the command endpoint to publish to:
    building/{building_id}/device/{device_key}/cmd

Required env vars:
    MQTT_HOST                  - EMQX broker host (shared with subscriber)
    MQTT_PORT                  - EMQX broker port  (default 1883)
    MQTT_SERVICE_CLIENT_ID     - MQTT client id for this publisher (default: "backend_publisher")
    MQTT_SERVICE_USER          - Username for the backend service account in EMQX
    MQTT_SERVICE_PASS          - Password for the backend service account in EMQX
"""

import json
import logging
import os
import threading

import paho.mqtt.client as mqtt

logger = logging.getLogger("mqtt_publisher")

_PUBLISH_TIMEOUT = 5  # seconds to wait for QoS-1 PUBACK


class _MQTTPublisher:
    def __init__(self) -> None:
        self._client = mqtt.Client(
            client_id=os.environ.get("MQTT_SERVICE_CLIENT_ID", "backend_publisher"),
            clean_session=True,
        )
        user = os.environ.get("MQTT_SERVICE_USER")
        pwd = os.environ.get("MQTT_SERVICE_PASS")
        if user:
            self._client.username_pw_set(user, pwd)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        host = os.environ["MQTT_HOST"]
        port = int(os.environ.get("MQTT_PORT", 1883))
        self._client.connect(host, port, keepalive=60)
        self._client.loop_start()

    @staticmethod
    def _on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTTPublisher connected to broker")
        else:
            logger.error("MQTTPublisher connect failed rc=%s", rc)

    @staticmethod
    def _on_disconnect(client, userdata, rc):
        if rc != 0:
            logger.warning("MQTTPublisher disconnected rc=%s, reconnect pending", rc)

    def publish(self, topic: str, payload: dict, qos: int = 1) -> bool:
        """Publish a JSON payload to topic. Returns True on success."""
        try:
            msg_info = self._client.publish(
                topic,
                json.dumps(payload),
                qos=qos,
                retain=False,
            )
            msg_info.wait_for_publish(timeout=_PUBLISH_TIMEOUT)
            return msg_info.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception:
            logger.exception("MQTT publish error topic=%s", topic)
            return False


_instance: "_MQTTPublisher | None" = None
_init_lock = threading.Lock()


def get_publisher() -> _MQTTPublisher:
    """Return the process-wide MQTT publisher (lazily initialised)."""
    global _instance
    if _instance is None:
        with _init_lock:
            if _instance is None:
                _instance = _MQTTPublisher()
    return _instance
