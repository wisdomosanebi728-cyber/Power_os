"""
POWER OS - Local Platform & Simulation Launcher
Run this script to start the Power_OS Gateway & Live Microgrid Dashboard locally.

Usage:
    python run_poweros.py
"""

import os
import sys
import uvicorn
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("poweros-runner")

# Add services and simulator to Python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, "services", "common"))
sys.path.insert(0, os.path.join(ROOT_DIR, "services", "auth-device-service"))
sys.path.insert(0, os.path.join(ROOT_DIR, "services", "energy-service"))
sys.path.insert(0, os.path.join(ROOT_DIR, "services", "forecasting-service"))
sys.path.insert(0, os.path.join(ROOT_DIR, "services", "optimization-service"))
sys.path.insert(0, os.path.join(ROOT_DIR, "services", "ingestion-service"))
sys.path.insert(0, os.path.join(ROOT_DIR, "services", "gateway-service"))
sys.path.insert(0, os.path.join(ROOT_DIR, "simulator"))


def main():
    logger.info("=======================================================")
    logger.info("  ⚡ POWER OS - Microgrid Management System ⚡")
    logger.info("=======================================================")
    logger.info("Starting Unified API Gateway & Real-Time Dashboard...")
    logger.info("Dashboard UI: http://localhost:8080")
    logger.info("Interactive OpenAPI Docs: http://localhost:8080/docs")
    logger.info("Live Telemetry WebSocket: ws://localhost:8080/ws/live/00000000-0000-0000-0000-000000000001")
    logger.info("=======================================================")

    from poweros_gateway.main import app

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    main()
