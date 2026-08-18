from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthDeviceConfig(BaseSettings):
    SERVICE_NAME: str = "auth-device-service"
    PORT: int = 8002
    HOST: str = "0.0.0.0"

    DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/power_os"
    JWT_SECRET: str = "power-os-insecure-development-secret-change-in-production-32bytes"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
