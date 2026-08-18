from typing import Dict, Any


class DieselGeneratorModel:
    """Simulates a commercial diesel backup generator with fuel consumption modeling."""

    def __init__(
        self,
        device_id: str,
        capacity_kw: float = 36.0,
        fuel_capacity_liters: float = 120.0,
        initial_fuel_liters: float = 100.0,
    ):
        self.device_id = device_id
        self.capacity_kw = capacity_kw
        self.fuel_capacity_liters = fuel_capacity_liters
        self.current_fuel_liters = initial_fuel_liters
        self.is_running = False
        self.engine_run_hours = 142.5
        self.coolant_temp_c = 28.0

    def step(self, requested_power_kw: float, dt_hours: float) -> Dict[str, Any]:
        """
        Executes a generator step.
        If requested_power_kw > 0 and fuel is available, outputs power and burns diesel.
        """
        if self.current_fuel_liters <= 0.5 or requested_power_kw <= 0.5:
            self.is_running = False
            actual_power_kw = 0.0
            self.coolant_temp_c = max(28.0, self.coolant_temp_c - 10.0 * dt_hours)
        else:
            self.is_running = True
            actual_power_kw = min(requested_power_kw, self.capacity_kw)
            self.engine_run_hours += dt_hours
            self.coolant_temp_c = min(88.0, self.coolant_temp_c + 30.0 * dt_hours)

            # Fuel consumption formula: Liters/hr = 0.24 * P + 0.04 * P_rated
            liters_per_hour = 0.24 * actual_power_kw + 0.04 * self.capacity_kw
            fuel_burned_liters = liters_per_hour * dt_hours
            self.current_fuel_liters = max(0.0, self.current_fuel_liters - fuel_burned_liters)

        fuel_level_percent = round((self.current_fuel_liters / self.fuel_capacity_liters) * 100.0, 1)

        return {
            "device_id": self.device_id,
            "source_type": "generator",
            "power_kw": round(actual_power_kw, 2),
            "fuel_level_percent": fuel_level_percent,
            "engine_run_hours": round(self.engine_run_hours, 2),
            "coolant_temp_c": round(self.coolant_temp_c, 1),
            "status": "active" if self.is_running else "standby",
        }
