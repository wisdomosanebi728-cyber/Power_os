import math
import random
from typing import Dict, List, Any


class ConsumerMeterModel:
    """Simulates an individual smart energy meter with distinct load profiles."""

    def __init__(
        self,
        device_id: str,
        consumer_type: str,
        nominal_kw: float,
        criticality: str = "medium",
        initial_kwh: float = 1000.0,
    ):
        self.device_id = device_id
        self.consumer_type = consumer_type
        self.nominal_kw = nominal_kw
        self.criticality = criticality
        self.cumulative_kwh = initial_kwh
        self.compressor_state = False
        self.compressor_timer = 0

    def update(self, hour_of_day: float, dt_hours: float) -> Dict[str, Any]:
        """Calculates instantaneous load consumption based on consumer archetype."""
        noise = random.uniform(-0.1, 0.1)

        if self.consumer_type == "residential":
            # Peaks: Morning 06:30 - 08:30 (~3.5 kW) and Evening 18:30 - 22:30 (~5.5 kW)
            base = 0.8
            if 6.5 <= hour_of_day <= 8.5:
                profile_factor = 2.8 + noise
            elif 18.0 <= hour_of_day <= 23.0:
                profile_factor = 4.2 + noise * 1.5
            elif 0.0 <= hour_of_day <= 5.5:
                profile_factor = 0.4 + noise * 0.2
            else:
                profile_factor = 1.2 + noise * 0.5
            power_kw = round(base * profile_factor, 2)

        elif self.consumer_type == "commercial_cold_store":
            # Baseline ~3.0 kW + 4.5 kW compressor cycle every 20-30 mins
            base = 3.2
            self.compressor_timer += 1
            if self.compressor_timer >= 6:  # Toggle cycle
                self.compressor_state = not self.compressor_state
                self.compressor_timer = 0
            compressor_kw = 4.5 if self.compressor_state else 0.0
            power_kw = round(base + compressor_kw + noise * 0.3, 2)

        elif self.consumer_type == "workshop_barber":
            # Daytime working hours: 08:00 - 18:00 with active spikes
            if 8.0 <= hour_of_day <= 18.5:
                base = 2.5
                spikes = random.choice([0.0, 1.2, 2.8, 4.0])
                power_kw = round(base + spikes + noise, 2)
            else:
                power_kw = round(0.2 + max(0.0, noise * 0.1), 2)

        elif self.consumer_type == "community_facility":
            # Streetlights / Facility evening load + Water pumping 10:00 - 14:00
            pump_kw = 4.0 if 10.0 <= hour_of_day <= 14.0 else 0.0
            lighting_kw = 2.2 if (hour_of_day >= 18.5 or hour_of_day <= 6.0) else 0.3
            power_kw = round(pump_kw + lighting_kw + noise * 0.2, 2)

        else:
            power_kw = round(self.nominal_kw * (1.0 + noise), 2)

        power_kw = max(0.05, power_kw)
        self.cumulative_kwh += power_kw * dt_hours

        return {
            "device_id": self.device_id,
            "source_type": "load",
            "consumer_type": self.consumer_type,
            "power_kw": power_kw,
            "cumulative_kwh": round(self.cumulative_kwh, 3),
            "voltage_v": 230.0 + random.uniform(-1.5, 1.5),
            "criticality": self.criticality,
            "status": "active",
        }
