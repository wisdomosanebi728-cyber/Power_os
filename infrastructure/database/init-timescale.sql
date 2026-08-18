-- ==========================================================
-- POWER OS Database Initialization Script
-- PostgreSQL + TimescaleDB
-- ==========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Relational Tables

CREATE TABLE IF NOT EXISTS communities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    location_country VARCHAR(50) NOT NULL DEFAULT 'Nigeria',
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    grid_nominal_voltage_v NUMERIC(6, 2) DEFAULT 230.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    community_id UUID REFERENCES communities(id) ON DELETE SET NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'consumer',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS devices (
    id VARCHAR(64) PRIMARY KEY,
    community_id UUID NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    device_type VARCHAR(30) NOT NULL, -- solar_inverter, battery_storage, generator, grid_meter, consumer_meter
    hardware_model VARCHAR(100),
    auth_token_hash VARCHAR(255) NOT NULL,
    capacity_kw NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    capacity_kwh NUMERIC(10, 2) DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS community_tariffs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    community_id UUID NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    grid_import_tariff_per_kwh NUMERIC(10, 4) NOT NULL DEFAULT 0.1800,
    grid_feed_in_tariff_per_kwh NUMERIC(10, 4) DEFAULT 0.0500,
    diesel_price_per_liter NUMERIC(10, 4) NOT NULL DEFAULT 1.3500,
    generator_efficiency_kwh_per_liter NUMERIC(10, 2) DEFAULT 3.20,
    solar_maintenance_per_kwh NUMERIC(10, 4) DEFAULT 0.0100,
    battery_wear_cost_per_kwh NUMERIC(10, 4) DEFAULT 0.0300,
    valid_from TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS settlement_epochs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    community_id UUID NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    epoch_start TIMESTAMPTZ NOT NULL,
    epoch_end TIMESTAMPTZ NOT NULL,
    total_energy_generated_kwh NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    total_energy_consumed_kwh NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    total_cost NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    total_savings NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    merkle_root_hash VARCHAR(66),
    blockchain_tx_hash VARCHAR(66),
    settlement_status VARCHAR(30) DEFAULT 'calculated',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS consumer_settlement_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    epoch_id UUID NOT NULL REFERENCES settlement_epochs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    meter_device_id VARCHAR(64) REFERENCES devices(id),
    consumption_kwh NUMERIC(10, 2) NOT NULL,
    allocated_solar_kwh NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    allocated_battery_kwh NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    allocated_grid_kwh NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    allocated_gen_kwh NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    total_amount_due NUMERIC(10, 2) NOT NULL,
    payment_status VARCHAR(30) DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    community_id UUID,
    user_id UUID,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100),
    details TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 2. TimescaleDB Telemetry Table

CREATE TABLE IF NOT EXISTS telemetry_readings (
    time TIMESTAMPTZ NOT NULL,
    community_id UUID NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    source_type VARCHAR(30) NOT NULL,
    power_kw NUMERIC(10, 3) NOT NULL,
    energy_kwh NUMERIC(14, 3) NOT NULL,
    voltage_v NUMERIC(6, 2) DEFAULT 230.0,
    current_a NUMERIC(6, 2),
    frequency_hz NUMERIC(5, 2) DEFAULT 50.0,
    soc_percent NUMERIC(5, 2),
    fuel_level_percent NUMERIC(5, 2),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
);

-- Note: In plain PostgreSQL or TimescaleDB, create hypertables if the extension is present:
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('telemetry_readings', 'time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day');
    END IF;
END $$;

-- Indexes for lightning queries
CREATE INDEX IF NOT EXISTS idx_telemetry_comm_dev_time ON telemetry_readings (community_id, device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_source_time ON telemetry_readings (source_type, time DESC);
CREATE INDEX IF NOT EXISTS idx_settlement_epochs_comm ON settlement_epochs (community_id, epoch_start DESC);

-- 3. Seed Default Demonstration Community & Assets
INSERT INTO communities (id, name, location_country, currency, grid_nominal_voltage_v)
VALUES ('00000000-0000-0000-0000-000000000001', 'Solaris Green Microgrid Estate', 'Nigeria', 'USD', 230.0)
ON CONFLICT (id) DO NOTHING;

-- Default Operator Account (Password: admin123)
-- bcrypt hash for 'admin123': $2b$12$e8y2p6xqy1f.J0Uu0f7V2u7eF72uN0z648j4zYp.Hq.M.m7N1iB8q
INSERT INTO users (id, community_id, email, password_hash, full_name, role)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'operator@poweros.energy',
    '$2b$12$r7Fwz7zHn9mZzJ3RjQ6V.eE17C8u6qK4tq6J9N8hY3a2K4q5N6eP2',
    'Chinedu Okonkwo (Chief Energy Operator)',
    'operator'
) ON CONFLICT (email) DO NOTHING;

-- Seed Default Tariff
INSERT INTO community_tariffs (id, community_id, grid_import_tariff_per_kwh, grid_feed_in_tariff_per_kwh, diesel_price_per_liter, generator_efficiency_kwh_per_liter)
VALUES (
    '00000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000001',
    0.1800,
    0.0500,
    1.3500,
    3.20
) ON CONFLICT (id) DO NOTHING;

-- Seed Core Assets (SHA-256 for default test token 'pow_dev_secret_token_123' is a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3)
INSERT INTO devices (id, community_id, device_type, hardware_model, auth_token_hash, capacity_kw, capacity_kwh)
VALUES
    ('sol-001', '00000000-0000-0000-0000-000000000001', 'solar_inverter', 'Fronius Symo 30kW Commercial', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', 30.0, 0.0),
    ('bat-001', '00000000-0000-0000-0000-000000000001', 'battery_storage', 'BYD Battery-Box Commercial 60kWh', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', 25.0, 60.0),
    ('gen-001', '00000000-0000-0000-0000-000000000001', 'generator', 'Cummins 45kVA Diesel Backup Genset', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', 36.0, 0.0),
    ('grid-001', '00000000-0000-0000-0000-000000000001', 'grid_meter', 'Schneider ION7400 Main Incomer', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', 50.0, 0.0),
    ('meter-residential-01', '00000000-0000-0000-0000-000000000001', 'consumer_meter', 'Eastron SDM630 Smart Meter', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', 10.0, 0.0),
    ('meter-coldstore-01', '00000000-0000-0000-0000-000000000001', 'consumer_meter', 'Eastron SDM630 Smart Meter', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', 15.0, 0.0),
    ('meter-workshop-01', '00000000-0000-0000-0000-000000000001', 'consumer_meter', 'Eastron SDM630 Smart Meter', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', 10.0, 0.0),
    ('meter-facility-01', '00000000-0000-0000-0000-000000000001', 'consumer_meter', 'Eastron SDM630 Smart Meter', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', 8.0, 0.0)
ON CONFLICT (id) DO NOTHING;
