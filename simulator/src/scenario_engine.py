from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from simulator.src.config import SimulatorConfig
from simulator.src.models.solar import SolarInverterModel
from simulator.src.models.battery import BatteryStorageModel
from simulator.src.models.generator import DieselGeneratorModel
from simulator.src.models.grid import GridIncomerModel
from simulator.src.models.consumers import ConsumerMeterModel


class ScenarioEngine:
    """
    Coordinates all microgrid assets and consumers, enforcing physical energy balance
    and applying operational scenarios.
    """

    def __init__(self, config: SimulatorConfig):
        self.config = config
        self.virtual_time = datetime(2026, 8, 15, 11, 0, 0, tzinfo=timezone.utc)  # Start at 11:00 AM (peak sun)
        self.active_scenario = config.DEFAULT_SCENARIO

        # Asset Instances
        self.solar = SolarInverterModel("sol-001", capacity_kw=config.SOLAR_CAPACITY_KW)
        self.battery = BatteryStorageModel(
            "bat-001",
            capacity_kwh=config.BATTERY_CAPACITY_KWH,
            max_charge_kw=config.BATTERY_MAX_CHARGE_KW,
            max_discharge_kw=config.BATTERY_MAX_DISCHARGE_KW,
            initial_soc=80.0,
            min_soc=config.BATTERY_MIN_SOC,
            max_soc=config.BATTERY_MAX_SOC,
        )
        self.generator = DieselGeneratorModel("gen-001", capacity_kw=config.GENERATOR_CAPACITY_KW)
        self.grid = GridIncomerModel("grid-001", capacity_kw=50.0, initial_available=True)

        # Consumer Meter Instances
        self.consumers = [
            ConsumerMeterModel("meter-residential-01", "residential", nominal_kw=8.0, criticality="medium"),
            ConsumerMeterModel("meter-coldstore-01", "commercial_cold_store", nominal_kw=10.0, criticality="high"),
            ConsumerMeterModel("meter-workshop-01", "workshop_barber", nominal_kw=6.0, criticality="medium"),
            ConsumerMeterModel("meter-facility-01", "community_facility", nominal_kw=5.0, criticality="low"),
        ]

    def set_scenario(self, scenario_name: str):
        """Switches active scenario: 'normal', 'storm', 'grid_outage', 'peak_stress'."""
        self.active_scenario = scenario_name

    def step(self) -> List[Dict[str, Any]]:
        """
        Advances the microgrid by one virtual time step and returns a list of telemetry packets.
        """
        # Advance virtual time
        dt_seconds = self.config.TICK_INTERVAL_SECONDS * self.config.TIME_ACCELERATION_FACTOR
        dt_hours = dt_seconds / 3600.0
        self.virtual_time += timedelta(seconds=dt_seconds)
        hour_of_day = self.virtual_time.hour + self.virtual_time.minute / 60.0

        # Scenario overrides
        cloud_override = None
        force_grid_outage = False

        if self.active_scenario == "storm":
            cloud_override = 0.85  # 85% solar drop due to heavy cloud cover
        elif self.active_scenario == "grid_outage":
            force_grid_outage = True
        elif self.active_scenario == "peak_stress":
            force_grid_outage = True
            cloud_override = 0.70

        # 1. Update Solar Generation
        solar_telemetry = self.solar.update(hour_of_day, dt_hours, cloud_override=cloud_override)
        solar_kw = solar_telemetry["power_kw"]

        # 2. Update Consumers and Calculate Total Demand
        consumer_telemetries = []
        total_demand_kw = 0.0
        for consumer in self.consumers:
            c_telem = consumer.update(hour_of_day, dt_hours)
            total_demand_kw += c_telem["power_kw"]
            consumer_telemetries.append(c_telem)

        # 3. Energy Balance Dispatch Simulation
        # Net balance = Generation - Demand
        net_balance_kw = solar_kw - total_demand_kw

        battery_power_request = 0.0
        grid_power_request = 0.0
        gen_power_request = 0.0

        if net_balance_kw > 0.0:
            # Solar Surplus -> Charge Battery first
            battery_power_request = -net_balance_kw  # Negative = Charge
            battery_telemetry = self.battery.step(battery_power_request, dt_hours)
            residual_surplus = net_balance_kw - abs(battery_telemetry["power_kw"])

            # If battery is full and surplus remains -> Feed-in to grid if available
            if residual_surplus > 0.1 and not force_grid_outage:
                grid_telemetry = self.grid.step(-residual_surplus, dt_hours, force_outage=force_grid_outage)
            else:
                grid_telemetry = self.grid.step(0.0, dt_hours, force_outage=force_grid_outage)

            gen_telemetry = self.generator.step(0.0, dt_hours)

        else:
            # Solar Deficit -> Must supply remainder
            deficit_kw = abs(net_balance_kw)

            # Try battery discharge first (cheapest & cleanest storage)
            battery_telemetry = self.battery.step(deficit_kw, dt_hours)
            battery_delivered_kw = battery_telemetry["power_kw"]
            remaining_deficit = deficit_kw - battery_delivered_kw

            if remaining_deficit > 0.1:
                # If grid is available, import from grid
                if not force_grid_outage and self.grid.is_available:
                    grid_telemetry = self.grid.step(remaining_deficit, dt_hours, force_outage=force_grid_outage)
                    grid_delivered = grid_telemetry["power_kw"]
                    unmet = remaining_deficit - grid_delivered
                else:
                    grid_telemetry = self.grid.step(0.0, dt_hours, force_outage=True)
                    unmet = remaining_deficit

                # If still unmet (grid down or capacity limit), start Diesel Generator
                if unmet > 0.1:
                    gen_telemetry = self.generator.step(unmet, dt_hours)
                else:
                    gen_telemetry = self.generator.step(0.0, dt_hours)
            else:
                grid_telemetry = self.grid.step(0.0, dt_hours, force_outage=force_grid_outage)
                gen_telemetry = self.generator.step(0.0, dt_hours)

        # Attach timestamps and community metadata
        iso_timestamp = self.virtual_time.isoformat()
        all_telemetries = [solar_telemetry, battery_telemetry, grid_telemetry, gen_telemetry] + consumer_telemetries
        for item in all_telemetries:
            item["timestamp"] = iso_timestamp
            item["community_id"] = self.config.COMMUNITY_ID

        return all_telemetries
