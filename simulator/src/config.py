from pydantic_settings import BaseSettings, SettingsConfigDict


class SimulatorConfig(BaseSettings):
    COMMUNITY_ID: str = "00000000-0000-0000-0000-000000000001"
    COMMUNITY_NAME: str = "Solaris Green Microgrid Estate"

    # MQTT Settings
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_KEEPALIVE: int = 60
    MQTT_CLIENT_ID: str = "poweros-energy-simulator"

    # Simulation Dynamics
    TICK_INTERVAL_SECONDS: float = 2.0  # Real-world sleep between ticks
    TIME_ACCELERATION_FACTOR: float = 60.0  # 1 real sec = 60 virtual secs (1 min)
    DEFAULT_SCENARIO: str = "normal"  # normal, storm, grid_outage, peak_stress

    # Asset Sizing
    SOLAR_CAPACITY_KW: float = 30.0
    BATTERY_CAPACITY_KWH: float = 60.0
    BATTERY_MAX_CHARGE_KW: float = 20.0
    BATTERY_MAX_DISCHARGE_KW: float = 25.0
    BATTERY_MIN_SOC: float = 20.0  # 20% protective reserve
    BATTERY_MAX_SOC: float = 95.0
    GENERATOR_CAPACITY_KW: float = 36.0
    GENERATOR_FUEL_CAPACITY_LITERS: float = 120.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
