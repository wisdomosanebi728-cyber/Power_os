from abc import ABC, abstractmethod
from typing import Dict, Any, Union
from poweros_common.schemas.telemetry import NormalizedTelemetry


class IDeviceAdapter(ABC):
    @property
    @abstractmethod
    def adapter_name(self) -> str:
        pass

    @abstractmethod
    def parse_payload(self, raw_data: Union[str, bytes, Dict[str, Any]]) -> NormalizedTelemetry:
        pass

    @abstractmethod
    def format_command(self, command_type: str, parameters: Dict[str, Any]) -> Union[str, bytes]:
        pass
