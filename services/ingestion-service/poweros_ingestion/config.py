from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestionConfig(BaseSettings):
    SERVICE_NAME: str = "ingestion-service"
    PORT: int = 8001
    HOST: str = "0.0.0.0"

    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_KEEPALIVE: int = 60
    MQTT_TOPIC_SUBSCRIPTION: str = "power-os/community/+/device/+/telemetry"
    MQTT_CLIENT_ID: str = "poweros-ingestion-gateway"

    DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/power_os"
    REDIS_URL: str = "redis://localhost:6379/0"

    BATCH_SIZE: int = 50
    BATCH_TIMEOUT_SECONDS: float = 1.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
