import math
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException
from poweros_common.schemas.energy import LiveEnergyState
from poweros_common.schemas.settlement import (
    SettlementEpochSummary,
    EpochCloseRequest,
    MerkleProofSchema,
)
from ..state_aggregator import EnergyStateAggregator
from ..anomaly_detector import AnomalyDetector
from ..settlement_engine import SettlementEngine
from ..merkle import MerkleTree

router = APIRouter(prefix="/api/v1/communities", tags=["Energy & Settlements"])

LATEST_SNAPSHOTS: Dict[str, List[Dict[str, Any]]] = {}
COMMUNITY_EPOCHS: Dict[str, List[SettlementEpochSummary]] = {}
EPOCH_TREES: Dict[str, MerkleTree] = {}


def get_default_seed_readings(community_id: str) -> List[Dict[str, Any]]:
    now_hour = datetime.now(timezone.utc).hour + datetime.now(timezone.utc).minute / 60.0
    solar_factor = max(0.0, math.sin(math.pi * (now_hour - 6.0) / 12.0)) if 6.0 <= now_hour <= 18.0 else 0.0

    return [
        {"device_id": "sol-001", "source_type": "solar", "power_kw": round(24.5 * solar_factor, 2), "community_id": community_id},
        {"device_id": "bat-001", "source_type": "battery", "power_kw": round(4.0 * (1.0 - solar_factor), 2), "soc_percent": 78.5, "stored_energy_kwh": 47.1, "health_percent": 99.2, "community_id": community_id},
        {"device_id": "grid-001", "source_type": "grid", "power_kw": 0.0, "status": "active", "available": True, "community_id": community_id},
        {"device_id": "gen-001", "source_type": "generator", "power_kw": 0.0, "fuel_level_percent": 88.0, "status": "standby", "community_id": community_id},
        {"device_id": "meter-residential-01", "source_type": "load", "consumer_type": "residential", "power_kw": 5.4, "criticality": "medium", "community_id": community_id},
        {"device_id": "meter-coldstore-01", "source_type": "load", "consumer_type": "commercial_cold_store", "power_kw": 7.2, "criticality": "high", "community_id": community_id},
        {"device_id": "meter-workshop-01", "source_type": "load", "consumer_type": "workshop_barber", "power_kw": 3.8, "criticality": "medium", "community_id": community_id},
        {"device_id": "meter-facility-01", "source_type": "load", "consumer_type": "community_facility", "power_kw": 2.1, "criticality": "low", "community_id": community_id},
    ]


@router.get("/{community_id}/energy/live", response_model=LiveEnergyState)
def get_live_energy_state(community_id: str):
    readings = LATEST_SNAPSHOTS.get(community_id) or get_default_seed_readings(community_id)
    return EnergyStateAggregator.calculate_live_state(readings, community_id)


@router.post("/{community_id}/energy/telemetry-snapshot")
def update_telemetry_snapshot(community_id: str, readings: List[Dict[str, Any]]):
    LATEST_SNAPSHOTS[community_id] = readings
    return {"status": "updated", "readings_count": len(readings)}


@router.get("/{community_id}/energy/alerts")
def get_energy_alerts(community_id: str):
    readings = LATEST_SNAPSHOTS.get(community_id) or get_default_seed_readings(community_id)
    state = EnergyStateAggregator.calculate_live_state(readings, community_id)
    alerts = AnomalyDetector.detect_anomalies(state)
    return {
        "community_id": community_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alerts_count": len(alerts),
        "alerts": alerts,
    }


@router.get("/{community_id}/energy/history")
def get_energy_history(community_id: str, range_hours: int = Query(24, ge=1, le=168)):
    now = datetime.now(timezone.utc)
    series = []
    for h in range(range_hours, -1, -1):
        t = now - timedelta(hours=h)
        hour_val = t.hour + t.minute / 60.0
        sol_factor = max(0.0, math.sin(math.pi * (hour_val - 6.0) / 12.0)) if 6.0 <= hour_val <= 18.0 else 0.0
        sol_kw = round(28.0 * sol_factor, 1)

        load_kw = round(12.0 + 8.0 * math.sin(math.pi * (hour_val - 8.0) / 10.0) + (4.0 if 18 <= hour_val <= 22 else 0.0), 1)
        bat_kw = round(max(-15.0, min(18.0, load_kw - sol_kw)), 1)
        grid_kw = round(max(0.0, load_kw - sol_kw - max(0.0, bat_kw)), 1)
        gen_kw = 0.0

        series.append({
            "timestamp": t.isoformat(),
            "solar_generation_kw": sol_kw,
            "battery_power_kw": bat_kw,
            "grid_import_kw": grid_kw,
            "generator_kw": gen_kw,
            "total_demand_kw": load_kw,
        })

    return {
        "community_id": community_id,
        "range_hours": range_hours,
        "data_points_count": len(series),
        "series": series,
    }


@router.get("/{community_id}/energy/esg")
def get_esg_metrics(community_id: str):
    """Computes carbon intensity, avoided CO2 emissions, and clean energy fraction."""
    readings = LATEST_SNAPSHOTS.get(community_id) or get_default_seed_readings(community_id)
    state = EnergyStateAggregator.calculate_live_state(readings, community_id)

    solar_kw = state.generation.solar_kw
    battery_kw = state.generation.battery_discharge_kw
    gen_kw = state.generation.generator_kw
    grid_kw = state.generation.grid_import_kw
    total_kw = state.generation.total_kw

    # Emissions factors: Diesel ~0.85 kg CO2/kWh, Grid ~0.45 kg CO2/kWh
    current_emission_rate_kg_h = round(gen_kw * 0.85 + grid_kw * 0.45, 2)
    # Avoided emissions compared to 100% diesel generator baseline
    avoided_emission_rate_kg_h = round((solar_kw + battery_kw) * 0.85, 2)
    clean_fraction = round(((solar_kw + battery_kw) / max(0.1, total_kw)) * 100.0, 1)

    return {
        "community_id": community_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "clean_energy_fraction_percent": min(100.0, clean_fraction),
        "current_emission_rate_kg_co2_per_hour": current_emission_rate_kg_h,
        "avoided_emission_rate_kg_co2_per_hour": avoided_emission_rate_kg_h,
        "estimated_daily_co2_avoided_kg": round(avoided_emission_rate_kg_h * 14.0, 1),
        "esg_rating": "AAA" if clean_fraction >= 90 else ("AA" if clean_fraction >= 75 else "A"),
    }


# ==========================================
# SETTLEMENT & CRYPTOGRAPHIC NOTARIZATION
# ==========================================

@router.post("/{community_id}/settlements/close-epoch", response_model=SettlementEpochSummary)
def close_settlement_epoch(community_id: str, req: Optional[EpochCloseRequest] = None):
    """Calculates billing epoch settlement, generates invoices, and notarizes Merkle root hash."""
    now = datetime.now(timezone.utc)
    epoch_start = now - timedelta(days=30)
    epoch_end = now

    consumer_meters = [
        {"user_id": "usr-001", "user_name": "Dr. Amadi (Community Clinic)", "device_id": "meter-facility-01", "consumption_kwh": 312.5},
        {"user_id": "usr-002", "user_name": "Tunde Agro Cold Storage", "device_id": "meter-coldstore-01", "consumption_kwh": 845.0},
        {"user_id": "usr-003", "user_name": "Chidi Metalworks Workshop", "device_id": "meter-workshop-01", "consumption_kwh": 420.0},
        {"user_id": "usr-004", "user_name": "Residential Cluster Alpha", "device_id": "meter-residential-01", "consumption_kwh": 650.0},
    ]

    gen_summary = {
        "solar_kwh": 1850.0,
        "battery_kwh": 320.0,
        "grid_kwh": 57.5,
        "generator_kwh": 0.0,
    }

    summary, tree = SettlementEngine.calculate_epoch_settlement(
        community_id=community_id,
        epoch_start=epoch_start,
        epoch_end=epoch_end,
        consumer_meters=consumer_meters,
        generation_summary=gen_summary,
    )

    if community_id not in COMMUNITY_EPOCHS:
        COMMUNITY_EPOCHS[community_id] = []
    COMMUNITY_EPOCHS[community_id].append(summary)
    EPOCH_TREES[summary.epoch_id] = tree

    return summary


@router.get("/{community_id}/settlements/epochs", response_model=List[SettlementEpochSummary])
def list_settlement_epochs(community_id: str):
    if community_id not in COMMUNITY_EPOCHS or not COMMUNITY_EPOCHS[community_id]:
        # Auto-seed initial closed epoch
        close_settlement_epoch(community_id)
    return COMMUNITY_EPOCHS.get(community_id, [])


@router.get("/{community_id}/settlements/epochs/{epoch_id}/proofs/{user_id}", response_model=MerkleProofSchema)
def get_merkle_proof_for_invoice(community_id: str, epoch_id: str, user_id: str):
    epochs = COMMUNITY_EPOCHS.get(community_id, [])
    epoch = next((e for e in epochs if e.epoch_id == epoch_id), None)
    if not epoch:
        raise HTTPException(status_code=404, detail="Settlement epoch not found")

    invoice_idx = next((i for i, inv in enumerate(epoch.invoices) if inv.user_id == user_id), None)
    if invoice_idx is None:
        raise HTTPException(status_code=404, detail=f"Invoice for user {user_id} not found in epoch")

    invoice = epoch.invoices[invoice_idx]
    tree = EPOCH_TREES.get(epoch_id)
    if not tree:
        tree = MerkleTree([inv.leaf_hash for inv in epoch.invoices])
        EPOCH_TREES[epoch_id] = tree

    proof = tree.get_proof(invoice_idx)
    verified = MerkleTree.verify_proof(invoice.leaf_hash, proof, epoch.merkle_root_hash)

    return MerkleProofSchema(
        leaf=invoice.leaf_hash,
        root=epoch.merkle_root_hash,
        proof=proof,
        verified=verified,
    )
