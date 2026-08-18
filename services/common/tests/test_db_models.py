import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from poweros_common.database import Base
from poweros_common.models.entities import (
    Community,
    User,
    Device,
    CommunityTariff,
    SettlementEpoch,
    ConsumerSettlementItem,
)


@pytest.fixture
def db_session():
    # In-memory SQLite for rapid unit testing of relational mapping
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_create_community_and_assets(db_session):
    community = Community(
        id=uuid.uuid4(),
        name="Lagos Tech Haven Microgrid",
        location_country="Nigeria",
        currency="USD",
    )
    db_session.add(community)
    db_session.commit()

    user = User(
        id=uuid.uuid4(),
        community_id=community.id,
        email="operator@lagostech.com",
        password_hash="hash123",
        full_name="Amina Bello",
        role="operator",
    )
    db_session.add(user)
    db_session.commit()

    device = Device(
        id="sol-lagos-01",
        community_id=community.id,
        owner_user_id=user.id,
        device_type="solar_inverter",
        auth_token_hash="fake_hash",
        capacity_kw=50.0,
    )
    db_session.add(device)
    db_session.commit()

    # Query back and verify relations
    queried_comm = db_session.query(Community).filter_by(name="Lagos Tech Haven Microgrid").first()
    assert queried_comm is not None
    assert len(queried_comm.users) == 1
    assert queried_comm.users[0].email == "operator@lagostech.com"
    assert len(queried_comm.devices) == 1
    assert queried_comm.devices[0].capacity_kw == 50.0
