from datetime import datetime, timezone
from typing import Dict, Any, Union
from poweros_common.schemas.telemetry import NormalizedTelemetry
from .base import IDeviceAdapter


class EastronModbusAdapter(IDeviceAdapter):
    @property
    def adapter_name(self) -> str:
        return "eastron_sdm630_v1"

    def parse_payload(self, raw_data: Union[str, bytes, Dict[str, Any]]) -> NormalizedTelemetry:
        if not isinstance(raw_data, dict):
            raise ValueError("EastronModbusAdapter expects parsed measurements dictionary")

        meas = raw_data.get("measurements", {})
        device_id = raw_data["device_id"]
        community_id = raw_data.get("community_id", "00000000-0000-0000-0000-000000000001")

        return NormalizedTelemetry(
            time=datetime.now(timezone.utc),
            community_id=community_id,
            device_id=device_id,
            source_type="load",
            power_kw=float(meas.get("active_power_kw", 0.0)),
            energy_kwh=float(meas.get("total_active_kwh", 0.0)),
            voltage_v=float(meas.get("line_voltage_v", 230.0)),
            current_a=float(meas.get("current_a", 0.0)),
            frequency_hz=float(meas.get("frequency_hz", 50.0)),
            status="active",
        )

    def format_command(self, command_type: str, parameters: Dict[str, Any]) -> Union[str, bytes]:
        return b"\x01\x05\x00\x00\xFF\x00\x8C\x3A"
