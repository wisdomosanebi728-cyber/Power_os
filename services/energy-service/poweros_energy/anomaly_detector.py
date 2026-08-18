from typing import List, Dict, Any
from poweros_common.schemas.energy import LiveEnergyState


class AnomalyDetector:
    """Evaluates live energy state and raises operational and safety alerts."""

    @staticmethod
    def detect_anomalies(state: LiveEnergyState) -> List[Dict[str, Any]]:
        alerts = []

        # 1. Grid Outage Alert
        if not state.grid_status.available:
            severity = "HIGH" if state.storage.state_of_charge_percent < 40.0 else "MEDIUM"
            alerts.append({
                "code": "GRID_OUTAGE",
                "severity": severity,
                "title": "National Grid Outage Active",
                "message": f"Grid disconnected. Microgrid operating in islanded mode. Battery at {state.storage.state_of_charge_percent}%.",
            })

        # 2. Low Battery Reserve
        if state.storage.state_of_charge_percent <= 25.0:
            alerts.append({
                "code": "LOW_BATTERY_RESERVE",
                "severity": "HIGH",
                "title": "Battery Depletion Warning",
                "message": f"Battery State-of-Charge is {state.storage.state_of_charge_percent}%, approaching 20% minimum safety reserve.",
            })

        # 3. Generator Low Fuel
        if state.generator_status.fuel_level_percent <= 20.0:
            alerts.append({
                "code": "GENERATOR_LOW_FUEL",
                "severity": "CRITICAL" if state.generator_status.fuel_level_percent <= 10.0 else "HIGH",
                "title": "Diesel Fuel Level Low",
                "message": f"Generator diesel tank at {state.generator_status.fuel_level_percent}%. Refueling required for continued backup.",
            })

        # 4. High Diesel Dependency / Inefficient Run
        if state.generator_status.running and state.generation.generator_kw > 0.5 * state.consumption.total_demand_kw:
            alerts.append({
                "code": "HIGH_DIESEL_DEPENDENCY",
                "severity": "MEDIUM",
                "title": "High Generator Operational Cost",
                "message": f"Diesel generator supplying {round(state.generation.generator_kw, 1)} kW ({round((state.generation.generator_kw / state.consumption.total_demand_kw) * 100, 1)}% of demand). LCOE is elevated at ${state.current_lcoe_per_kwh}/kWh.",
            })

        # 5. Deficit / Load Shedding Risk
        available_supply = (
            state.generation.solar_kw +
            (state.storage.battery_stored_kwh * 0.9 if state.storage.state_of_charge_percent > 20.0 else 0.0) +
            (state.grid_status.current_power_kw if state.grid_status.available else 0.0) +
            36.0  # Max gen capacity
        )
        if state.consumption.total_demand_kw > available_supply:
            alerts.append({
                "code": "SHORTAGE_RISK",
                "severity": "CRITICAL",
                "title": "Potential Microgrid Deficit",
                "message": "Aggregate demand exceeds instantaneous capacity. Non-critical load shedding recommended.",
            })

        return alerts
