from pydantic_settings import BaseSettings, SettingsConfigDict


class ForecastingConfig(BaseSettings):
    SERVICE_NAME: str = "forecasting-service"
    PORT: int = 8004
    HOST: str = "0.0.0.0"

    DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/power_os"
    DEFAULT_SOLAR_CAPACITY_KW: float = 30.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
