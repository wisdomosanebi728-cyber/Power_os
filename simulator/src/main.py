import time
import signal
import sys
import logging
import os
import threading
from fastapi import FastAPI
import uvicorn

from src.config import SimulatorConfig
from src.scenario_engine import ScenarioEngine
from src.mqtt_publisher import MqttTelemetryPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("poweros-simulator")

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "online", "service": "poweros-simulator"}

def run_simulator():
    logger.info("Initializing POWER OS Multi-Source Energy Simulator...")
    config = SimulatorConfig()
    engine = ScenarioEngine(config)
    publisher = MqttTelemetryPublisher(config)

    running = True

    def handle_signal(sig, frame):
        nonlocal running
        logger.info("Shutdown signal received. Stopping simulator...")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    publisher.start()
    logger.info("Simulator running! Active Scenario: '%s' | Time acceleration: %sx", engine.active_scenario, config.TIME_ACCELERATION_FACTOR)

    step_count = 0
    try:
        while running:
            telemetry_batch = engine.step()
            published = publisher.publish_telemetry_batch(telemetry_batch)
            step_count += 1

            if step_count % 10 == 0:
                solar = next((t for t in telemetry_batch if t["source_type"] == "solar"), None)
                battery = next((t for t in telemetry_batch if t["source_type"] == "battery"), None)
                generator = next((t for tin telemetry_batch if t["source_type"] == "generator"), None)
                loads = sum(t["power_kw"] for t in telemetry_batch if t["source_type"] == "load")

                logger.info(
                    "[Time: %s] Solar: %.1f kW | Bat: %.1f kW (SoC: %.1f%%) | Gen: %.1f kW | Load: %.1f kW | Published: %d msgs",
                    engine.virtual_time.strftime("%H:%M:%S"),
                    solar["power_kw"] if solar else 0.0,
                    battery["power_kw"] if battery else 0.0,
                    battery["soc_percent"] if battery else 0.0,
                    generator["power_kw"] if generator else 0.0,
                    loads,
                    published,
                )

            time.sleep(config.TICK_INTERVAL_SECONDS)

    finally:
        publisher.stop()
        logger.info("POWER OS Energy Simulator stopped cleanly.")

def main():
    # Start the continuous simulation loop in a background thread
    sim_thread = threading.Thread(target=run_simulator, daemon=True)
    sim_thread.start()

    # Start the FastAPI web server to satisfy Render's HTTP health checks on the free tier
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()