from datetime import datetime, timezone
from typing import Dict, Any, Union
import json
from poweros_common.schemas.telemetry import NormalizedTelemetry
from .base import IDeviceAdapter


class SunSpecModbusAdapter(IDeviceAdapter):
    @property
    def adapter_name(self) -> str:
        return "sunspec_modbus_v1"

    def parse_payload(self, raw_data: Union[str, bytes, Dict[str, Any]]) -> NormalizedTelemetry:
        if not isinstance(raw_data, dict):
            raise ValueError("SunSpec adapter expects parsed register dictionary")

        regs = raw_data.get("registers", {})
        device_id = raw_data["device_id"]
        community_id = raw_data.get("community_id", "00000000-0000-0000-0000-000000000001")

        w_raw = regs.get("W", 0)
        w_sf = regs.get("W_SF", 0)
        power_kw = round((w_raw * (10 ** w_sf)) / 1000.0, 3)

        wh_raw = regs.get("WH", 0)
        wh_sf = regs.get("WH_SF", 0)
        energy_kwh = round((wh_raw * (10 ** wh_sf)) / 1000.0, 3)

        v_raw = regs.get("PhVphA", 2300)
        v_sf = regs.get("PhV_SF", -1)
        voltage_v = round(v_raw * (10 ** v_sf), 2)

        hz_raw = regs.get("Hz", 5000)
        hz_sf = regs.get("Hz_SF", -2)
        frequency_hz = round(hz_raw * (10 ** hz_sf), 2)

        soc_percent = None
        if "SoC" in regs:
            soc_raw = regs["SoC"]
            soc_sf = regs.get("SoC_SF", -1)
            soc_percent = round(soc_raw * (10 ** soc_sf), 2)

        source_type = "battery" if soc_percent is not None else "solar"
        status = "active" if power_kw != 0.0 else "standby"

        return NormalizedTelemetry(
            time=datetime.now(timezone.utc),
            community_id=community_id,
            device_id=device_id,
            source_type=source_type,
            power_kw=power_kw,
            energy_kwh=energy_kwh,
            voltage_v=voltage_v,
            frequency_hz=frequency_hz,
            soc_percent=soc_percent,
            status=status,
        )

    def format_command(self, command_type: str, parameters: Dict[str, Any]) -> Union[str, bytes]:
        target_kw = parameters.get("power_limit_kw", 0.0)
        return json.dumps({"register": 40234, "value": int(target_kw * 100)})
