import math
import random
from typing import Dict, Any


class SolarInverterModel:
    """Simulates a commercial grid-tied solar PV inverter with diurnal curves and cloud attenuation."""

    def __init__(self, device_id: str, capacity_kw: float = 30.0):
        self.device_id = device_id
        self.capacity_kw = capacity_kw
        self.cumulative_yield_kwh = 0.0
        self.cloud_factor = 0.0  # 0.0 = clear sky, 0.8 = heavy cloud cover

    def update(self, hour_of_day: float, dt_hours: float, cloud_override: float = None) -> Dict[str, Any]:
        """
        Calculates instantaneous solar power based on solar elevation angle.
        Sunrise ~06:00, Solar Noon ~12:00, Sunset ~18:00.
        """
        if cloud_override is not None:
            self.cloud_factor = cloud_override
        else:
            # Small random drift in cloud cover
            self.cloud_factor = max(0.0, min(0.85, self.cloud_factor + random.uniform(-0.05, 0.05)))

        if 6.0 <= hour_of_day <= 18.0:
            # Diurnal sine approximation
            solar_angle_rad = math.pi * (hour_of_day - 6.0) / 12.0
            theoretical_irradiance = math.sin(solar_angle_rad) * 1000.0  # W/m^2 peak
            actual_irradiance = max(0.0, theoretical_irradiance * (1.0 - self.cloud_factor))

            # Temperature derating: ambient heats up during peak sun
            ambient_temp_c = 25.0 + 10.0 * math.sin(solar_angle_rad)
            panel_temp_c = ambient_temp_c + (actual_irradiance / 800.0) * 25.0
            temp_derating = 1.0 - max(0.0, (panel_temp_c - 25.0) * 0.004)  # -0.4%/°C above 25°C

            # Efficiency ~97%
            inverter_eff = 0.97
            power_kw = round((actual_irradiance / 1000.0) * self.capacity_kw * temp_derating * inverter_eff, 2)
            power_kw = max(0.0, min(self.capacity_kw, power_kw))
        else:
            actual_irradiance = 0.0
            panel_temp_c = 22.0
            power_kw = 0.0

        # Accumulate daily kWh
        energy_kwh = power_kw * dt_hours
        self.cumulative_yield_kwh = round(self.cumulative_yield_kwh + energy_kwh, 3)

        return {
            "device_id": self.device_id,
            "source_type": "solar",
            "power_kw": power_kw,
            "daily_yield_kwh": self.cumulative_yield_kwh,
            "irradiance_w_m2": round(actual_irradiance, 1),
            "temperature_c": round(panel_temp_c, 1),
            "status": "active" if power_kw > 0.05 else "standby",
        }
