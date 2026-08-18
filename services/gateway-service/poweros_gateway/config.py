from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewayConfig(BaseSettings):
    SERVICE_NAME: str = "gateway-service"
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    AUTH_SERVICE_URL: str = "http://localhost:8000"
    INGESTION_SERVICE_URL: str = "http://localhost:8001"
    ENERGY_SERVICE_URL: str = "http://localhost:8002"
    FORECASTING_SERVICE_URL: str = "http://localhost:8003"
    OPTIMIZATION_SERVICE_URL: str = "http://localhost:8004"

    REDIS_URL: str = "redis://localhost:6379/0"
    STATIC_DIR: str = "static"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
