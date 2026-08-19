import json
import time
import logging
from typing import Dict, Any, List
import paho.mqtt.client as mqtt
from src.config import SimulatorConfig

logger = logging.getLogger("poweros-simulator-publisher")


class MqttTelemetryPublisher:
    """Manages connection to MQTT broker and publishes microgrid telemetry."""

    def __init__(self, config: SimulatorConfig):
        self.config = config
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=config.MQTT_CLIENT_ID,
        )
        self.is_connected = False

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.is_connected = True
            logger.info("Successfully connected to MQTT broker at %s:%d", self.config.MQTT_HOST, self.config.MQTT_PORT)
        else:
            logger.error("Failed to connect to MQTT broker, return code: %s", rc)

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        self.is_connected = False
        logger.warning("Disconnected from MQTT broker. Will attempt auto-reconnect.")

    def start(self):
        """Connects to broker in non-blocking background loop."""
        try:
            self.client.connect(
                self.config.MQTT_HOST,
                self.config.MQTT_PORT,
                self.config.MQTT_KEEPALIVE,
            )
            self.client.loop_start()
        except Exception as e:
            logger.warning("Initial MQTT connection failed (%s). Simulator will continue and retry.", str(e))

    def stop(self):
        """Stops background loop and disconnects."""
        self.client.loop_stop()
        self.client.disconnect()

    def publish_telemetry_batch(self, telemetry_items: List[Dict[str, Any]]) -> int:
        """
        Publishes a list of telemetry packets to their respective device MQTT topics:
        power-os/community/{community_id}/device/{device_id}/telemetry
        """
        published_count = 0
        for item in telemetry_items:
            community_id = item.get("community_id", self.config.COMMUNITY_ID)
            device_id = item["device_id"]
            topic = f"power-os/community/{community_id}/device/{device_id}/telemetry"
            payload = json.dumps(item)

            if self.is_connected:
                self.client.publish(topic, payload, qos=1)
                published_count += 1

        return published_count
