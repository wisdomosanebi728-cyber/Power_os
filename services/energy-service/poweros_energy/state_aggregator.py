from datetime import datetime, timezone
from typing import Dict, List, Any
from poweros_common.schemas.energy import (
    LiveEnergyState,
    GenerationMix,
    StorageState,
    ConsumptionBreakdown,
    GridState,
    GeneratorState,
)


class EnergyStateAggregator:
    """Aggregates telemetry into structured live energy balance states."""

    @staticmethod
    def calculate_live_state(readings: List[Dict[str, Any]], community_id: str) -> LiveEnergyState:
        solar_kw = 0.0
        battery_power_kw = 0.0
        battery_soc = 80.0
        battery_capacity = 60.0
        battery_stored = 48.0
        battery_health = 99.0
        grid_kw = 0.0
        grid_available = True
        gen_kw = 0.0
        gen_fuel = 85.0
        gen_running = False

        total_demand_kw = 0.0
        breakdown_by_category: Dict[str, float] = {
            "residential": 0.0,
            "commercial_cold_store": 0.0,
            "workshop_barber": 0.0,
            "community_facility": 0.0,
        }
        critical_load_kw = 0.0
        non_critical_load_kw = 0.0

        for r in readings:
            src = r.get("source_type", "")
            p_kw = float(r.get("power_kw", 0.0))

            if src == "solar":
                solar_kw += max(0.0, p_kw)
            elif src == "battery":
                battery_power_kw += p_kw
                if r.get("soc_percent") is not None:
                    battery_soc = float(r["soc_percent"])
                if r.get("stored_energy_kwh") is not None:
                    battery_stored = float(r["stored_energy_kwh"])
                if r.get("health_percent") is not None:
                    battery_health = float(r["health_percent"])
            elif src == "grid":
                grid_kw += max(0.0, p_kw)
                grid_available = r.get("status") != "offline" and r.get("available", True)
            elif src == "generator":
                gen_kw += max(0.0, p_kw)
                if r.get("fuel_level_percent") is not None:
                    gen_fuel = float(r["fuel_level_percent"])
                gen_running = gen_kw > 0.1
            elif src == "load":
                total_demand_kw += max(0.0, p_kw)
                cat = r.get("consumer_type", "residential")
                breakdown_by_category[cat] = round(breakdown_by_category.get(cat, 0.0) + p_kw, 2)
                crit = r.get("criticality", "medium")
                if crit == "high":
                    critical_load_kw += p_kw
                else:
                    non_critical_load_kw += p_kw

        battery_discharge_kw = max(0.0, battery_power_kw)
        battery_charging_kw = abs(min(0.0, battery_power_kw))
        total_gen_kw = round(solar_kw + battery_discharge_kw + grid_kw + gen_kw, 2)

        if total_gen_kw > 0:
            weighted_cost = (
                solar_kw * 0.01 +
                battery_discharge_kw * 0.03 +
                grid_kw * 0.18 +
                gen_kw * 0.42
            )
            current_lcoe = round(weighted_cost / total_gen_kw, 4)
        else:
            current_lcoe = 0.01

        return LiveEnergyState(
            timestamp=datetime.now(timezone.utc),
            community_id=community_id,
            generation=GenerationMix(
                solar_kw=round(solar_kw, 2),
                battery_discharge_kw=round(battery_discharge_kw, 2),
                grid_import_kw=round(grid_kw, 2),
                generator_kw=round(gen_kw, 2),
                total_kw=total_gen_kw,
            ),
            storage=StorageState(
                battery_capacity_kwh=battery_capacity,
                battery_stored_kwh=battery_stored,
                state_of_charge_percent=battery_soc,
                battery_charging_kw=round(battery_charging_kw, 2),
                battery_health_percent=battery_health,
            ),
            consumption=ConsumptionBreakdown(
                total_demand_kw=round(total_demand_kw, 2),
                breakdown_by_category=breakdown_by_category,
                critical_load_kw=round(critical_load_kw, 2),
                non_critical_load_kw=round(non_critical_load_kw, 2),
            ),
            grid_status=GridState(
                available=grid_available,
                current_power_kw=round(grid_kw, 2),
                tariff_per_kwh=0.18,
            ),
            generator_status=GeneratorState(
                running=gen_running,
                current_output_kw=round(gen_kw, 2),
                fuel_level_percent=gen_fuel,
                cost_per_kwh=0.42,
            ),
            current_lcoe_per_kwh=current_lcoe,
        )
