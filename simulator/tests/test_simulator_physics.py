from simulator.src.config import SimulatorConfig
from simulator.src.models.solar import SolarInverterModel
from simulator.src.models.battery import BatteryStorageModel
from simulator.src.models.generator import DieselGeneratorModel
from simulator.src.models.consumers import ConsumerMeterModel
from simulator.src.scenario_engine import ScenarioEngine


def test_solar_inverter_diurnal_curve():
    solar = SolarInverterModel("sol-001", capacity_kw=30.0)

    # Midnight (00:00) -> 0 kW
    night_telemetry = solar.update(hour_of_day=0.0, dt_hours=0.01)
    assert night_telemetry["power_kw"] == 0.0
    assert night_telemetry["irradiance_w_m2"] == 0.0

    # Solar Noon (12:00) -> High positive generation
    noon_telemetry = solar.update(hour_of_day=12.0, dt_hours=0.01, cloud_override=0.0)
    assert noon_telemetry["power_kw"] > 20.0
    assert noon_telemetry["irradiance_w_m2"] > 800.0


def test_battery_storage_limits():
    battery = BatteryStorageModel(
        device_id="bat-001",
        capacity_kwh=60.0,
        max_discharge_kw=25.0,
        initial_soc=22.0,
        min_soc=20.0,
        max_soc=95.0,
    )

    # Attempt massive discharge when near min_soc
    telemetry = battery.step(requested_power_kw=25.0, dt_hours=1.0)
    # Must enforce min_soc boundary
    assert battery.soc_percent >= 20.0
    assert telemetry["power_kw"] <= 25.0

    # Further discharge request at 20% SoC must deliver 0 kW
    battery.soc_percent = 20.0
    zero_telemetry = battery.step(requested_power_kw=10.0, dt_hours=0.1)
    assert zero_telemetry["power_kw"] == 0.0
    assert battery.soc_percent >= 20.0


def test_generator_fuel_and_power():
    gen = DieselGeneratorModel(device_id="gen-001", capacity_kw=36.0, fuel_capacity_liters=100.0)
    initial_fuel = gen.current_fuel_liters

    # Standby -> No fuel burned
    gen.step(requested_power_kw=0.0, dt_hours=1.0)
    assert gen.current_fuel_liters == initial_fuel
    assert gen.is_running is False

    # Running at 20 kW -> Fuel burned
    gen.step(requested_power_kw=20.0, dt_hours=1.0)
    assert gen.current_fuel_liters < initial_fuel
    assert gen.is_running is True


def test_scenario_engine_stepping():
    config = SimulatorConfig()
    engine = ScenarioEngine(config)

    # Step normal scenario
    batch = engine.step()
    assert len(batch) >= 8  # solar, battery, grid, gen + 4 consumers

    device_ids = {t["device_id"] for t in batch}
    assert "sol-001" in device_ids
    assert "bat-001" in device_ids
    assert "gen-001" in device_ids
    assert "grid-001" in device_ids
    assert "meter-residential-01" in device_ids
    assert "meter-coldstore-01" in device_ids


def test_grid_outage_scenario():
    config = SimulatorConfig()
    engine = ScenarioEngine(config)
    engine.set_scenario("grid_outage")

    batch = engine.step()
    grid_telem = next(t for t in batch if t["device_id"] == "grid-001")
    assert grid_telem["available"] is False
    assert grid_telem["power_kw"] == 0.0
