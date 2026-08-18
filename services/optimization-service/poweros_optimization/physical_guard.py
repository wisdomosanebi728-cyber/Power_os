from typing import Tuple
from poweros_common.schemas.optimization import DispatchStrategy, OptimizationRequest


class PhysicalGuard:
    """
    Deterministic Safety & Invariant Guard Layer.
    Audits and clamps all optimization directives before emission, ensuring
    physical energy and battery conservation laws can never be violated.
    """

    @classmethod
    def audit_and_enforce(
        cls,
        strategy: DispatchStrategy,
        req: OptimizationRequest,
        min_soc: float = 20.0,
        max_soc: float = 95.0,
        max_inverter_kw: float = 40.0,
        max_charge_kw: float = 20.0,
        max_discharge_kw: float = 25.0,
    ) -> Tuple[DispatchStrategy, bool]:
        """
        Enforces physical bounds:
        1. Solar clamped to available irradiance
        2. Battery discharge clamped to usable SoC reserve
        3. Battery charge clamped to remaining capacity headroom
        4. Generator clamped to rated capacity
        5. Energy conservation balance preserved
        """
        violation_detected = False

        # 1. Guard Solar
        actual_solar_kw = min(strategy.solar_target_kw, req.available_solar_kw)
        if actual_solar_kw != strategy.solar_target_kw:
            violation_detected = True

        # 2. Guard Battery Discharge
        usable_soc = max(0.0, req.battery_soc_percent - min_soc)
        usable_energy_kwh = (usable_soc / 100.0) * req.battery_capacity_kwh
        max_deliverable_kw = min(max_discharge_kw, usable_energy_kwh)

        actual_bat_dis_kw = min(strategy.battery_discharge_target_kw, max_deliverable_kw)
        if actual_bat_dis_kw != strategy.battery_discharge_target_kw:
            violation_detected = True

        # 3. Guard Battery Charge
        headroom_soc = max(0.0, max_soc - req.battery_soc_percent)
        headroom_kwh = (headroom_soc / 100.0) * req.battery_capacity_kwh
        max_absorbable_kw = min(max_charge_kw, headroom_kwh)

        actual_bat_ch_kw = min(strategy.battery_charge_target_kw, max_absorbable_kw)
        if actual_bat_ch_kw != strategy.battery_charge_target_kw:
            violation_detected = True

        # 4. Guard Grid Import
        actual_grid_kw = strategy.grid_import_target_kw if req.grid_available else 0.0
        if actual_grid_kw != strategy.grid_import_target_kw:
            violation_detected = True

        # 5. Guard Generator
        max_gen = req.generator_rated_kw if req.generator_available else 0.0
        actual_gen_kw = min(strategy.generator_target_kw, max_gen)
        if actual_gen_kw != strategy.generator_target_kw:
            violation_detected = True

        # 6. Reconcile Energy Balance
        supply = actual_solar_kw + actual_bat_dis_kw + actual_grid_kw + actual_gen_kw - actual_bat_ch_kw
        shed_load_kw = max(0.0, req.current_demand_kw - supply)

        guarded_strategy = DispatchStrategy(
            solar_target_kw=round(actual_solar_kw, 2),
            battery_discharge_target_kw=round(actual_bat_dis_kw, 2),
            battery_charge_target_kw=round(actual_bat_ch_kw, 2),
            grid_import_target_kw=round(actual_grid_kw, 2),
            generator_target_kw=round(actual_gen_kw, 2),
            curtailed_solar_kw=round(max(0.0, req.available_solar_kw - actual_solar_kw - actual_bat_ch_kw), 2),
            shed_load_kw=round(shed_load_kw, 2),
        )

        return guarded_strategy, violation_detected
