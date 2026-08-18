from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class BaseAppConfig(BaseSettings):
    """Base application settings inherited by all POWER OS microservices."""

    APP_NAME: str = "POWER OS"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Security
    JWT_SECRET: str = "power-os-insecure-development-secret-change-in-production-32bytes"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/power_os"
    TIMESCALE_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/power_os"

    # MQTT
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_KEEPALIVE: int = 60
    MQTT_CLIENT_ID: Optional[str] = None
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Blockchain
    RPC_URL: str = "http://localhost:8545"
    SETTLEMENT_CONTRACT_ADDRESS: Optional[str] = None
    PRIVATE_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
