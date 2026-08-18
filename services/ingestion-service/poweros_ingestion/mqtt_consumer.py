import logging
import paho.mqtt.client as mqtt
from .config import IngestionConfig
from .adapters.simulator_adapter import SimulatorJsonAdapter
from .buffer_writer import TelemetryBufferWriter

logger = logging.getLogger("poweros-mqtt-consumer")


class MqttTelemetryConsumer:
    def __init__(self, config: IngestionConfig, buffer_writer: TelemetryBufferWriter):
        self.config = config
        self.buffer_writer = buffer_writer
        self.adapter = SimulatorJsonAdapter()
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=config.MQTT_CLIENT_ID,
        )
        self.is_connected = False

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.is_connected = True
            logger.info("Ingestion Gateway connected to MQTT Broker. Subscribing to: %s", self.config.MQTT_TOPIC_SUBSCRIPTION)
            client.subscribe(self.config.MQTT_TOPIC_SUBSCRIPTION, qos=1)
        else:
            logger.error("Failed to connect to MQTT broker, rc: %s", rc)

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        self.is_connected = False
        logger.warning("Ingestion Gateway disconnected from MQTT broker.")

    def _on_message(self, client, userdata, msg):
        try:
            normalized = self.adapter.parse_payload(msg.payload)
            self.buffer_writer.add(normalized)
        except Exception as e:
            logger.warning("Failed to process MQTT message on topic %s: %s", msg.topic, str(e))

    def start(self):
        try:
            self.client.connect(
                self.config.MQTT_HOST,
                self.config.MQTT_PORT,
                self.config.MQTT_KEEPALIVE,
            )
            self.client.loop_start()
        except Exception as e:
            logger.warning("Could not connect to MQTT Broker on startup (%s). Will retry in background.", str(e))

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
