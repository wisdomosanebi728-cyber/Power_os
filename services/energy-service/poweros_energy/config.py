from pydantic_settings import BaseSettings, SettingsConfigDict


class EnergyConfig(BaseSettings):
    SERVICE_NAME: str = "energy-service"
    PORT: int = 8003
    HOST: str = "0.0.0.0"

    DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/power_os"
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
