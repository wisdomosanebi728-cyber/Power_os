from pydantic_settings import BaseSettings, SettingsConfigDict


class OptimizationConfig(BaseSettings):
    SERVICE_NAME: str = "optimization-service"
    PORT: int = 8005
    HOST: str = "0.0.0.0"

    DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/power_os"

    # Default Economic Parameters
    SOLAR_LCOE_PER_KWH: float = 0.0100
    BATTERY_WEAR_PER_KWH: float = 0.0300
    GRID_DEFAULT_TARIFF_PER_KWH: float = 0.1800
    DIESEL_DEFAULT_COST_PER_KWH: float = 0.4200
    UNMET_DEMAND_PENALTY_PER_KWH: float = 2.5000

    # Physical Default Invariants
    BATTERY_MIN_SOC: float = 20.0  # %
    BATTERY_MAX_SOC: float = 95.0  # %

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
