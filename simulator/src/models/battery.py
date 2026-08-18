from typing import Dict, Any


class BatteryStorageModel:
    """Simulates a commercial Battery Energy Storage System (BESS) with Coulomb counting and power limits."""

    def __init__(
        self,
        device_id: str,
        capacity_kwh: float = 60.0,
        max_charge_kw: float = 20.0,
        max_discharge_kw: float = 25.0,
        initial_soc: float = 75.0,
        min_soc: float = 20.0,
        max_soc: float = 95.0,
        efficiency: float = 0.95,
    ):
        self.device_id = device_id
        self.capacity_kwh = capacity_kwh
        self.max_charge_kw = max_charge_kw
        self.max_discharge_kw = max_discharge_kw
        self.soc_percent = initial_soc
        self.min_soc = min_soc
        self.max_soc = max_soc
        self.efficiency = efficiency
        self.nominal_voltage_v = 51.2
        self.health_percent = 99.2
        self.cycles = 142

    def step(self, requested_power_kw: float, dt_hours: float) -> Dict[str, Any]:
        """
        Executes a battery time step.
        - requested_power_kw < 0: Charging (from excess solar/grid)
        - requested_power_kw > 0: Discharging (to meet community demand)
        Enforces physical bounds: cannot discharge below min_soc or charge above max_soc.
        """
        actual_power_kw = 0.0

        if requested_power_kw > 0.0:
            # Discharging
            usable_energy_kwh = max(0.0, (self.soc_percent - self.min_soc) / 100.0 * self.capacity_kwh)
            max_deliverable_kw = min(self.max_discharge_kw, (usable_energy_kwh / dt_hours) * self.efficiency if dt_hours > 0 else 0.0)
            actual_power_kw = min(requested_power_kw, max_deliverable_kw)

            # Energy drained from chemical storage (including loss)
            energy_drained_kwh = (actual_power_kw / self.efficiency) * dt_hours
            delta_soc = (energy_drained_kwh / self.capacity_kwh) * 100.0
            self.soc_percent = max(self.min_soc, self.soc_percent - delta_soc)

        elif requested_power_kw < 0.0:
            # Charging
            charge_power_target = abs(requested_power_kw)
            headroom_kwh = max(0.0, (self.max_soc - self.soc_percent) / 100.0 * self.capacity_kwh)
            max_absorbable_kw = min(self.max_charge_kw, (headroom_kwh / dt_hours) / self.efficiency if dt_hours > 0 else 0.0)
            actual_power_kw = -min(charge_power_target, max_absorbable_kw)

            # Chemical energy gained
            energy_gained_kwh = abs(actual_power_kw) * self.efficiency * dt_hours
            delta_soc = (energy_gained_kwh / self.capacity_kwh) * 100.0
            self.soc_percent = min(self.max_soc, self.soc_percent + delta_soc)

        self.soc_percent = round(self.soc_percent, 2)
        stored_energy_kwh = round((self.soc_percent / 100.0) * self.capacity_kwh, 2)

        # Approximate current from DC bus voltage
        current_a = round((actual_power_kw * 1000.0) / self.nominal_voltage_v, 1)

        status = "standby"
        if actual_power_kw > 0.1:
            status = "discharging"
        elif actual_power_kw < -0.1:
            status = "charging"

        return {
            "device_id": self.device_id,
            "source_type": "battery",
            "power_kw": round(actual_power_kw, 2),
            "soc_percent": self.soc_percent,
            "stored_energy_kwh": stored_energy_kwh,
            "voltage_v": self.nominal_voltage_v,
            "current_a": current_a,
            "health_percent": self.health_percent,
            "status": status,
        }
