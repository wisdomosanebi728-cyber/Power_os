import time
import logging
import json
import threading
from typing import List, Optional
from sqlalchemy import text
from poweros_common.schemas.telemetry import NormalizedTelemetry
from poweros_common.database import get_engine, get_session_factory
from .config import IngestionConfig

logger = logging.getLogger("poweros-buffer-writer")


class TelemetryBufferWriter:
    def __init__(self, config: IngestionConfig):
        self.config = config
        self.buffer: List[NormalizedTelemetry] = []
        self.lock = threading.Lock()
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None

        try:
            self.engine = get_engine(config.DATABASE_URL)
            self.session_factory = get_session_factory(self.engine)
            self.db_available = True
        except Exception as e:
            logger.warning("Database not immediately available (%s). Buffer will run in memory.", str(e))
            self.engine = None
            self.session_factory = None
            self.db_available = False

        self.redis_client = None
        try:
            import redis
            self.redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
            self.redis_client.ping()
        except Exception as e:
            logger.warning("Redis not immediately available (%s).", str(e))
            self.redis_client = None

        self.total_ingested = 0
        self.total_flushed = 0
        self.total_dropped = 0

    def add(self, telemetry: NormalizedTelemetry):
        with self.lock:
            self.buffer.append(telemetry)
            self.total_ingested += 1
            buffer_len = len(self.buffer)

        if buffer_len >= self.config.BATCH_SIZE:
            self.flush()

    def start(self):
        self.running = True
        self.worker_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Telemetry buffer writer thread started.")

    def stop(self):
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        self.flush()

    def _flush_loop(self):
        while self.running:
            time.sleep(self.config.BATCH_TIMEOUT_SECONDS)
            self.flush()

    def flush(self) -> int:
        with self.lock:
            if not self.buffer:
                return 0
            items_to_write = list(self.buffer)
            self.buffer.clear()

        if self.redis_client:
            try:
                for item in items_to_write:
                    channel = f"telemetry:{item.community_id}:{item.device_id}"
                    payload_json = json.dumps(item.model_dump(), default=str)
                    self.redis_client.publish(channel, payload_json)
                    self.redis_client.publish("telemetry:stream", payload_json)
            except Exception as e:
                logger.debug("Redis broadcast error: %s", str(e))

        if self.session_factory:
            try:
                with self.session_factory() as session:
                    insert_stmt = text("""
                        INSERT INTO telemetry_readings (
                            time, community_id, device_id, source_type,
                            power_kw, energy_kwh, voltage_v, current_a,
                            frequency_hz, soc_percent, fuel_level_percent, status
                        ) VALUES (
                            :time, :community_id, :device_id, :source_type,
                            :power_kw, :energy_kwh, :voltage_v, :current_a,
                            :frequency_hz, :soc_percent, :fuel_level_percent, :status
                        )
                    """)
                    records = [item.model_dump() for item in items_to_write]
                    session.execute(insert_stmt, records)
                    session.commit()
                    self.total_flushed += len(items_to_write)
            except Exception as e:
                logger.error("Failed to batch insert %d telemetry records: %s", len(items_to_write), str(e))
                self.total_dropped += len(items_to_write)
        else:
            self.total_flushed += len(items_to_write)

        return len(items_to_write)
