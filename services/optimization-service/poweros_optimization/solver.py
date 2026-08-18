from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from poweros_common.schemas.optimization import (
    DispatchAction,
    DispatchStrategy,
    FinancialImpact,
    ShortageRisk,
    OptimizationRecommendation,
    OptimizationRequest,
)
from .physical_guard import PhysicalGuard
from .config import OptimizationConfig


class EconomicDispatchSolver:
    """
    Solves the constrained microgrid economic dispatch optimization problem,
    minimizing Levelized Cost of Energy (LCOE) while strictly honoring physical bounds.
    """

    def __init__(self, config: OptimizationConfig):
        self.config = config

    def solve(self, req: OptimizationRequest) -> OptimizationRecommendation:
        demand = req.current_demand_kw
        solar_avail = req.available_solar_kw
        soc = req.battery_soc_percent
        cap_kwh = req.battery_capacity_kwh
        min_soc = self.config.BATTERY_MIN_SOC

        # Calculate usable battery reserve
        usable_soc = max(0.0, soc - min_soc)
        usable_energy_kwh = (usable_soc / 100.0) * cap_kwh
        max_discharge_kw = min(25.0, usable_energy_kwh)

        # 1. Economic Dispatch Hierarchy: Solar -> Battery -> Grid -> Generator
        solar_dispatch = min(demand, solar_avail)
        remaining_demand = demand - solar_dispatch

        surplus_solar = max(0.0, solar_avail - solar_dispatch)
        battery_charge = 0.0
        battery_discharge = 0.0
        grid_import = 0.0
        gen_dispatch = 0.0

        if surplus_solar > 0.1:
            # Charge battery with excess solar
            headroom_kwh = max(0.0, (self.config.BATTERY_MAX_SOC - soc) / 100.0 * cap_kwh)
            battery_charge = min(surplus_solar, min(20.0, headroom_kwh))
            action = DispatchAction.CHARGE_BATTERY_SURPLUS_SOLAR
        else:
            if remaining_demand > 0.0:
                # Discharge battery
                battery_discharge = min(remaining_demand, max_discharge_kw)
                remaining_demand -= battery_discharge

            if remaining_demand > 0.0:
                # Use grid if available
                if req.grid_available:
                    grid_import = min(remaining_demand, 50.0)
                    remaining_demand -= grid_import

            if remaining_demand > 0.0:
                # Use diesel generator as last resort
                if req.generator_available:
                    gen_dispatch = min(remaining_demand, req.generator_rated_kw)
                    remaining_demand -= gen_dispatch

            # Determine high-level action
            if gen_dispatch > 0.1:
                action = DispatchAction.DISPATCH_GENERATOR_BACKUP
            elif grid_import > 0.1 and battery_discharge > 0.1:
                action = DispatchAction.DISPATCH_SOLAR_BATTERY_GRID
            elif grid_import > 0.1:
                action = DispatchAction.DISPATCH_SOLAR_AND_GRID
            elif battery_discharge > 0.1:
                action = DispatchAction.DISPATCH_SOLAR_AND_BATTERY
            else:
                action = DispatchAction.DISPATCH_SOLAR_ONLY

        raw_strategy = DispatchStrategy(
            solar_target_kw=solar_dispatch,
            battery_discharge_target_kw=battery_discharge,
            battery_charge_target_kw=battery_charge,
            grid_import_target_kw=grid_import,
            generator_target_kw=gen_dispatch,
            curtailed_solar_kw=max(0.0, surplus_solar - battery_charge),
            shed_load_kw=remaining_demand,
        )

        # 2. Run Physical Guard
        guarded_strategy, _ = PhysicalGuard.audit_and_enforce(
            raw_strategy,
            req,
            min_soc=self.config.BATTERY_MIN_SOC,
            max_soc=self.config.BATTERY_MAX_SOC,
        )

        # 3. Calculate Financial Impact & Avoided Generator Costs
        # Cost per source
        c_solar = guarded_strategy.solar_target_kw * self.config.SOLAR_LCOE_PER_KWH
        c_bat = guarded_strategy.battery_discharge_target_kw * self.config.BATTERY_WEAR_PER_KWH
        c_grid = guarded_strategy.grid_import_target_kw * req.grid_tariff_per_kwh
        c_gen = guarded_strategy.generator_target_kw * (req.diesel_price_per_liter / req.generator_efficiency_kwh_l)

        current_cost_rate = round(c_solar + c_bat + c_grid + c_gen, 2)

        # Unoptimized baseline: 100% diesel generator run
        diesel_kwh_cost = req.diesel_price_per_liter / req.generator_efficiency_kwh_l
        baseline_cost_rate = round(demand * diesel_kwh_cost, 2)
        hourly_savings = round(max(0.0, baseline_cost_rate - current_cost_rate), 2)
        savings_pct = round((hourly_savings / baseline_cost_rate) * 100.0, 1) if baseline_cost_rate > 0 else 0.0

        delivered_power = guarded_strategy.solar_target_kw + guarded_strategy.battery_discharge_target_kw + guarded_strategy.grid_import_target_kw + guarded_strategy.generator_target_kw
        lcoe = round(current_cost_rate / delivered_power, 4) if delivered_power > 0 else 0.01

        # 4. Shortage & Autonomy Assessment
        autonomy_hours = round(usable_energy_kwh / max(1.0, demand - guarded_strategy.solar_target_kw), 1) if demand > guarded_strategy.solar_target_kw else 12.0
        risk_level = "LOW"
        if autonomy_hours < 1.0 and not req.grid_available and req.generator_rated_kw < demand:
            risk_level = "CRITICAL"
        elif autonomy_hours < 2.5 and not req.grid_available:
            risk_level = "HIGH"
        elif autonomy_hours < 4.0:
            risk_level = "MODERATE"

        # 5. Formulate Explainable Natural Language Recommendation
        explanation_parts = []
        if guarded_strategy.solar_target_kw > 0:
            pct = round((guarded_strategy.solar_target_kw / max(0.1, demand)) * 100, 1)
            explanation_parts.append(f"Solar PV satisfies {pct}% of load ({guarded_strategy.solar_target_kw} kW).")
        if guarded_strategy.battery_discharge_target_kw > 0:
            explanation_parts.append(f"Battery storage supplies {guarded_strategy.battery_discharge_target_kw} kW (SoC: {soc}%).")
        if guarded_strategy.grid_import_target_kw > 0:
            explanation_parts.append(f"Grid imports {guarded_strategy.grid_import_target_kw} kW at ${req.grid_tariff_per_kwh}/kWh.")
        if guarded_strategy.generator_target_kw > 0:
            explanation_parts.append(f"Diesel backup active for {guarded_strategy.generator_target_kw} kW deficit.")
        elif baseline_cost_rate > 0:
            explanation_parts.append(f"Generator remains OFF, saving ${round(diesel_kwh_cost * demand, 2)}/hour in fuel burn.")

        explanation = " ".join(explanation_parts)

        return OptimizationRecommendation(
            timestamp=datetime.now(timezone.utc),
            community_id=req.community_id,
            action=action,
            confidence=0.96,
            strategy_details=guarded_strategy,
            explanation=explanation,
            financial_impact=FinancialImpact(
                current_cost_rate_per_hour=current_cost_rate,
                unoptimized_baseline_cost_per_hour=baseline_cost_rate,
                hourly_savings=hourly_savings,
                savings_percentage=savings_pct,
                levelized_cost_per_kwh=lcoe,
            ),
            shortage_risk=ShortageRisk(
                risk_level=risk_level,
                projected_deficit_kwh=guarded_strategy.shed_load_kw,
                hours_of_battery_autonomy=autonomy_hours,
            ),
            physical_guards_verified=True,
        )
