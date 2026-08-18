import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from poweros_common.database import Base
from poweros_common.models.entities import Community
from poweros_auth_device.main import app


@pytest.fixture
def client_with_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    app.state.engine = engine
    app.state.session_factory = session_factory

    # Seed test community
    db = session_factory()
    comm = Community(name="Abuja Eco Microgrid", location_country="Nigeria")
    db.add(comm)
    db.commit()
    comm_id = str(comm.id)
    db.close()

    client = TestClient(app)
    return client, comm_id


def test_user_registration_and_login(client_with_db):
    client, comm_id = client_with_db

    # 1. Register User
    reg_payload = {
        "email": "operator.amina@poweros.energy",
        "password": "Password123!",
        "full_name": "Amina Bello",
        "role": "operator",
        "community_id": comm_id,
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == "operator.amina@poweros.energy"
    assert user_data["role"] == "operator"

    # 2. Login
    login_payload = {
        "email": "operator.amina@poweros.energy",
        "password": "Password123!",
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 3. Get /me
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "operator.amina@poweros.energy"


def test_device_provisioning(client_with_db):
    client, comm_id = client_with_db

    prov_payload = {
        "device_id": "sol-abuja-01",
        "device_type": "solar_inverter",
        "hardware_model": "SMA Sunny Tripower 25kW",
        "capacity_kw": 25.0,
        "capacity_kwh": 0.0,
    }
    prov_res = client.post(f"/api/v1/communities/{comm_id}/devices/provision", json=prov_payload)
    assert prov_res.status_code == 201
    dev_data = prov_res.json()
    assert dev_data["device_id"] == "sol-abuja-01"
    assert dev_data["raw_auth_token"].startswith("pow_dev_")
    assert dev_data["mqtt_telemetry_topic"] == f"power-os/community/{comm_id}/device/sol-abuja-01/telemetry"

    # Verify listed
    list_res = client.get(f"/api/v1/communities/{comm_id}/devices")
    assert list_res.status_code == 200
    devices = list_res.json()
    assert len(devices) == 1
    assert devices[0]["id"] == "sol-abuja-01"
