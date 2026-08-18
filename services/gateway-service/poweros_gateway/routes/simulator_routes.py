import math
from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import APIRouter
from pydantic import BaseModel
from poweros_energy.routes.energy_routes import LATEST_SNAPSHOTS

router = APIRouter(prefix="/api/v1/simulator", tags=["Simulator Control"])


class ScenarioTriggerRequest(BaseModel):
    community_id: str = "00000000-0000-0000-0000-000000000001"
    scenario: str  # "normal", "cloud_pass", "grid_blackout", "heatwave_surge", "generator_failover"
    solar_capacity_kw: float = 30.0
    battery_capacity_kwh: float = 60.0


CURRENT_SCENARIO: Dict[str, str] = {}


@router.post("/trigger")
def trigger_scenario(req: ScenarioTriggerRequest):
    CURRENT_SCENARIO[req.community_id] = req.scenario
    cid = req.community_id
    sc = req.scenario

    if sc == "cloud_pass":
        # Solar drop to 15%, battery discharges heavily
        readings = [
            {"device_id": "sol-001", "source_type": "solar", "power_kw": 4.2, "community_id": cid},
            {"device_id": "bat-001", "source_type": "battery", "power_kw": 14.5, "soc_percent": 62.0, "stored_energy_kwh": 37.2, "health_percent": 99.0, "community_id": cid},
            {"device_id": "grid-001", "source_type": "grid", "power_kw": 0.0, "status": "active", "available": True, "community_id": cid},
            {"device_id": "gen-001", "source_type": "generator", "power_kw": 0.0, "fuel_level_percent": 88.0, "status": "standby", "community_id": cid},
            {"device_id": "meter-residential-01", "source_type": "load", "consumer_type": "residential", "power_kw": 6.5, "criticality": "medium", "community_id": cid},
            {"device_id": "meter-coldstore-01", "source_type": "load", "consumer_type": "commercial_cold_store", "power_kw": 7.8, "criticality": "high", "community_id": cid},
            {"device_id": "meter-workshop-01", "source_type": "load", "consumer_type": "workshop_barber", "power_kw": 4.4, "criticality": "medium", "community_id": cid},
        ]
    elif sc == "grid_blackout":
        # Grid goes offline, microgrid islands onto Solar + BESS + Genset backup
        readings = [
            {"device_id": "sol-001", "source_type": "solar", "power_kw": 18.0, "community_id": cid},
            {"device_id": "bat-001", "source_type": "battery", "power_kw": 8.0, "soc_percent": 45.0, "stored_energy_kwh": 27.0, "health_percent": 98.8, "community_id": cid},
            {"device_id": "grid-001", "source_type": "grid", "power_kw": 0.0, "status": "offline", "available": False, "community_id": cid},
            {"device_id": "gen-001", "source_type": "generator", "power_kw": 0.0, "fuel_level_percent": 85.0, "status": "standby", "community_id": cid},
            {"device_id": "meter-residential-01", "source_type": "load", "consumer_type": "residential", "power_kw": 7.0, "criticality": "medium", "community_id": cid},
            {"device_id": "meter-coldstore-01", "source_type": "load", "consumer_type": "commercial_cold_store", "power_kw": 11.0, "criticality": "high", "community_id": cid},
            {"device_id": "meter-workshop-01", "source_type": "load", "consumer_type": "workshop_barber", "power_kw": 5.0, "criticality": "medium", "community_id": cid},
            {"device_id": "meter-facility-01", "source_type": "load", "consumer_type": "community_facility", "power_kw": 3.0, "criticality": "low", "community_id": cid},
        ]
    elif sc == "heatwave_surge":
        # High solar + massive AC/cooling load spike + battery at limit
        readings = [
            {"device_id": "sol-001", "source_type": "solar", "power_kw": 28.5, "community_id": cid},
            {"device_id": "bat-001", "source_type": "battery", "power_kw": 12.0, "soc_percent": 54.0, "stored_energy_kwh": 32.4, "health_percent": 98.5, "community_id": cid},
            {"device_id": "grid-001", "source_type": "grid", "power_kw": 10.0, "status": "active", "available": True, "community_id": cid},
            {"device_id": "gen-001", "source_type": "generator", "power_kw": 0.0, "fuel_level_percent": 84.0, "status": "standby", "community_id": cid},
            {"device_id": "meter-residential-01", "source_type": "load", "consumer_type": "residential", "power_kw": 14.2, "criticality": "medium", "community_id": cid},
            {"device_id": "meter-coldstore-01", "source_type": "load", "consumer_type": "commercial_cold_store", "power_kw": 22.0, "criticality": "high", "community_id": cid},
            {"device_id": "meter-workshop-01", "source_type": "load", "consumer_type": "workshop_barber", "power_kw": 9.5, "criticality": "medium", "community_id": cid},
            {"device_id": "meter-facility-01", "source_type": "load", "consumer_type": "community_facility", "power_kw": 4.8, "criticality": "low", "community_id": cid},
        ]
    elif sc == "generator_failover":
        # Zero solar (night) + Low battery + Diesel Gen running
        readings = [
            {"device_id": "sol-001", "source_type": "solar", "power_kw": 0.0, "community_id": cid},
            {"device_id": "bat-001", "source_type": "battery", "power_kw": 2.0, "soc_percent": 18.5, "stored_energy_kwh": 11.1, "health_percent": 98.2, "community_id": cid},
            {"device_id": "grid-001", "source_type": "grid", "power_kw": 0.0, "status": "offline", "available": False, "community_id": cid},
            {"device_id": "gen-001", "source_type": "generator", "power_kw": 22.0, "fuel_level_percent": 68.0, "status": "active", "community_id": cid},
            {"device_id": "meter-residential-01", "source_type": "load", "consumer_type": "residential", "power_kw": 8.0, "criticality": "medium", "community_id": cid},
            {"device_id": "meter-coldstore-01", "source_type": "load", "consumer_type": "commercial_cold_store", "power_kw": 12.0, "criticality": "high", "community_id": cid},
            {"device_id": "meter-workshop-01", "source_type": "load", "consumer_type": "workshop_barber", "power_kw": 4.0, "criticality": "medium", "community_id": cid},
        ]
    else:  # "normal"
        # Standard balanced afternoon
        readings = [
            {"device_id": "sol-001", "source_type": "solar", "power_kw": 26.0, "community_id": cid},
            {"device_id": "bat-001", "source_type": "battery", "power_kw": -6.5, "soc_percent": 82.0, "stored_energy_kwh": 49.2, "health_percent": 99.4, "community_id": cid},
            {"device_id": "grid-001", "source_type": "grid", "power_kw": 0.0, "status": "active", "available": True, "community_id": cid},
            {"device_id": "gen-001", "source_type": "generator", "power_kw": 0.0, "fuel_level_percent": 92.0, "status": "standby", "community_id": cid},
            {"device_id": "meter-residential-01", "source_type": "load", "consumer_type": "residential", "power_kw": 6.0, "criticality": "medium", "community_id": cid},
            {"device_id": "meter-coldstore-01", "source_type": "load", "consumer_type": "commercial_cold_store", "power_kw": 7.5, "criticality": "high", "community_id": cid},
            {"device_id": "meter-workshop-01", "source_type": "load", "consumer_type": "workshop_barber", "power_kw": 4.0, "criticality": "medium", "community_id": cid},
            {"device_id": "meter-facility-01", "source_type": "load", "consumer_type": "community_facility", "power_kw": 2.0, "criticality": "low", "community_id": cid},
        ]

    LATEST_SNAPSHOTS[cid] = readings
    return {
        "status": "scenario_applied",
        "community_id": cid,
        "scenario": sc,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "devices_affected": len(readings),
    }


@router.get("/status/{community_id}")
def get_scenario_status(community_id: str):
    return {
        "community_id": community_id,
        "active_scenario": CURRENT_SCENARIO.get(community_id, "normal"),
    }
