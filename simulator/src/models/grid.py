from typing import Dict, Any


class GridIncomerModel:
    """Simulates national grid feeder with availability toggles and import metering."""

    def __init__(self, device_id: str, capacity_kw: float = 50.0, initial_available: bool = True):
        self.device_id = device_id
        self.capacity_kw = capacity_kw
        self.is_available = initial_available
        self.cumulative_import_kwh = 12450.0
        self.cumulative_export_kwh = 850.0
        self.voltage_v = 230.0
        self.frequency_hz = 50.0

    def step(self, requested_power_kw: float, dt_hours: float, force_outage: bool = False) -> Dict[str, Any]:
        """
        requested_power_kw > 0: Importing power from utility grid
        requested_power_kw < 0: Exporting surplus solar to grid (Feed-in)
        """
        if force_outage:
            self.is_available = False

        if not self.is_available:
            return {
                "device_id": self.device_id,
                "source_type": "grid",
                "power_kw": 0.0,
                "voltage_v": 0.0,
                "frequency_hz": 0.0,
                "status": "offline",
                "available": False,
            }

        # Grid is available
        actual_power_kw = min(requested_power_kw, self.capacity_kw)
        if actual_power_kw > 0:
            self.cumulative_import_kwh += actual_power_kw * dt_hours
        elif actual_power_kw < 0:
            self.cumulative_export_kwh += abs(actual_power_kw) * dt_hours

        return {
            "device_id": self.device_id,
            "source_type": "grid",
            "power_kw": round(actual_power_kw, 2),
            "voltage_v": self.voltage_v,
            "frequency_hz": self.frequency_hz,
            "cumulative_import_kwh": round(self.cumulative_import_kwh, 2),
            "status": "active",
            "available": True,
        }
