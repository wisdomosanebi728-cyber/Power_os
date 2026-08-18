from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class ConsumerInvoice(BaseModel):
    user_id: str
    user_name: str
    meter_device_id: str
    consumption_kwh: float = Field(..., ge=0.0)
    allocated_solar_kwh: float = Field(..., ge=0.0)
    allocated_battery_kwh: float = Field(..., ge=0.0)
    allocated_grid_kwh: float = Field(..., ge=0.0)
    allocated_gen_kwh: float = Field(..., ge=0.0)
    blended_tariff_per_kwh: float = Field(..., ge=0.0)
    total_amount_due: float = Field(..., ge=0.0)
    payment_status: str = "pending"
    leaf_hash: Optional[str] = None


class SettlementEpochSummary(BaseModel):
    epoch_id: str
    community_id: str
    epoch_start: datetime
    epoch_end: datetime
    total_energy_generated_kwh: float
    total_energy_consumed_kwh: float
    total_cost: float
    total_savings: float
    merkle_root_hash: Optional[str] = None
    blockchain_tx_hash: Optional[str] = None
    settlement_status: str = "calculated"
    invoices: List[ConsumerInvoice] = Field(default_factory=list)


class MerkleProofItem(BaseModel):
    position: str = Field(..., description="'left' or 'right'")
    data: str = Field(..., description="32-byte hex string")


class MerkleProofSchema(BaseModel):
    leaf: str
    root: str
    proof: List[MerkleProofItem]
    verified: bool


class EpochCloseRequest(BaseModel):
    community_id: str
    notarize_on_chain: bool = True
