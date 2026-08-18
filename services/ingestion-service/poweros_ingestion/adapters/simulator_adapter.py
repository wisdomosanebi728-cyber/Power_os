import json
from datetime import datetime, timezone
from typing import Dict, Any, Union
from poweros_common.schemas.telemetry import NormalizedTelemetry
from .base import IDeviceAdapter


class SimulatorJsonAdapter(IDeviceAdapter):
    @property
    def adapter_name(self) -> str:
        return "simulator_json_v1"

    def parse_payload(self, raw_data: Union[str, bytes, Dict[str, Any]]) -> NormalizedTelemetry:
        if isinstance(raw_data, bytes):
            data = json.loads(raw_data.decode("utf-8"))
        elif isinstance(raw_data, str):
            data = json.loads(raw_data)
        else:
            data = raw_data

        raw_time = data.get("timestamp")
        if raw_time:
            if isinstance(raw_time, str):
                time_val = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            else:
                time_val = raw_time
        else:
            time_val = datetime.now(timezone.utc)

        energy_kwh = (
            data.get("daily_yield_kwh")
            or data.get("cumulative_kwh")
            or data.get("stored_energy_kwh")
            or data.get("cumulative_import_kwh")
            or 0.0
        )

        return NormalizedTelemetry(
            time=time_val,
            community_id=data.get("community_id", "00000000-0000-0000-0000-000000000001"),
            device_id=data["device_id"],
            source_type=data["source_type"],
            power_kw=float(data.get("power_kw", 0.0)),
            energy_kwh=float(energy_kwh),
            voltage_v=float(data.get("voltage_v", 230.0)),
            current_a=float(data.get("current_a", 0.0)) if data.get("current_a") is not None else None,
            frequency_hz=float(data.get("frequency_hz", 50.0)),
            soc_percent=float(data["soc_percent"]) if "soc_percent" in data else None,
            fuel_level_percent=float(data["fuel_level_percent"]) if "fuel_level_percent" in data else None,
            status=data.get("status", "active"),
        )

    def format_command(self, command_type: str, parameters: Dict[str, Any]) -> Union[str, bytes]:
        payload = {
            "command": command_type,
            "params": parameters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return json.dumps(payload)
