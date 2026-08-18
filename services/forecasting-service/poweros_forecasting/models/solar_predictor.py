import math
from datetime import datetime, timedelta
from typing import List


class SolarPredictor:
    """Predicts 24-hour solar PV generation curves based on solar irradiance physics."""

    @classmethod
    def predict_24h_solar(cls, base_time: datetime, solar_capacity_kw: float = 30.0) -> List[float]:
        solar_yields: List[float] = []

        for h in range(1, 25):
            target_time = base_time + timedelta(hours=h)
            hour_val = target_time.hour + target_time.minute / 60.0

            if 6.0 <= hour_val <= 18.0:
                angle_rad = math.pi * (hour_val - 6.0) / 12.0
                clearsky_factor = math.sin(angle_rad)
                # Apply typical ambient temperature derating ~0.94
                power_kw = round(solar_capacity_kw * clearsky_factor * 0.94, 2)
            else:
                power_kw = 0.0

            solar_yields.append(max(0.0, power_kw))

        return solar_yields
