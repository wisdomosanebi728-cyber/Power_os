import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Numeric,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from poweros_common.database import Base


class Community(Base):
    __tablename__ = "communities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    location_country = Column(String(50), nullable=False, default="Nigeria")
    currency = Column(String(10), nullable=False, default="USD")
    grid_nominal_voltage_v = Column(Numeric(6, 2), default=230.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    users = relationship("User", back_populates="community", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="community", cascade="all, delete-orphan")
    tariffs = relationship("CommunityTariff", back_populates="community", cascade="all, delete-orphan")
    settlement_epochs = relationship("SettlementEpoch", back_populates="community", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey("communities.id", ondelete="SET NULL"), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(30), nullable=False, default="consumer")  # operator, admin, consumer, auditor
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    community = relationship("Community", back_populates="users")
    owned_devices = relationship("Device", back_populates="owner")
    settlement_items = relationship("ConsumerSettlementItem", back_populates="user")


class Device(Base):
    __tablename__ = "devices"

    id = Column(String(64), primary_key=True)  # e.g., 'sol-001', 'bat-001', 'gen-001', 'meter-101'
    community_id = Column(UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    device_type = Column(String(30), nullable=False)  # solar_inverter, battery_storage, generator, grid_meter, consumer_meter
    hardware_model = Column(String(100), nullable=True)
    auth_token_hash = Column(String(255), nullable=False)
    capacity_kw = Column(Numeric(10, 2), nullable=False, default=0.0)
    capacity_kwh = Column(Numeric(10, 2), nullable=True, default=0.0)  # for storage
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    community = relationship("Community", back_populates="devices")
    owner = relationship("User", back_populates="owned_devices")


class CommunityTariff(Base):
    __tablename__ = "community_tariffs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    grid_import_tariff_per_kwh = Column(Numeric(10, 4), nullable=False, default=0.18)
    grid_feed_in_tariff_per_kwh = Column(Numeric(10, 4), nullable=False, default=0.05)
    diesel_price_per_liter = Column(Numeric(10, 4), nullable=False, default=1.35)
    generator_efficiency_kwh_per_liter = Column(Numeric(10, 2), nullable=False, default=3.20)
    solar_maintenance_per_kwh = Column(Numeric(10, 4), nullable=False, default=0.01)
    battery_wear_cost_per_kwh = Column(Numeric(10, 4), nullable=False, default=0.03)
    valid_from = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    community = relationship("Community", back_populates="tariffs")


class SettlementEpoch(Base):
    __tablename__ = "settlement_epochs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    epoch_start = Column(DateTime(timezone=True), nullable=False)
    epoch_end = Column(DateTime(timezone=True), nullable=False)
    total_energy_generated_kwh = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_energy_consumed_kwh = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_cost = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_savings = Column(Numeric(12, 2), nullable=False, default=0.0)
    merkle_root_hash = Column(String(66), nullable=True)  # 0x + 64 hex chars
    blockchain_tx_hash = Column(String(66), nullable=True)
    settlement_status = Column(String(30), nullable=False, default="calculated")  # calculated, notarized, finalized
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    community = relationship("Community", back_populates="settlement_epochs")
    items = relationship("ConsumerSettlementItem", back_populates="epoch", cascade="all, delete-orphan")


class ConsumerSettlementItem(Base):
    __tablename__ = "consumer_settlement_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    epoch_id = Column(UUID(as_uuid=True), ForeignKey("settlement_epochs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    meter_device_id = Column(String(64), ForeignKey("devices.id"), nullable=True)
    consumption_kwh = Column(Numeric(10, 2), nullable=False)
    allocated_solar_kwh = Column(Numeric(10, 2), nullable=False, default=0.0)
    allocated_battery_kwh = Column(Numeric(10, 2), nullable=False, default=0.0)
    allocated_grid_kwh = Column(Numeric(10, 2), nullable=False, default=0.0)
    allocated_gen_kwh = Column(Numeric(10, 2), nullable=False, default=0.0)
    total_amount_due = Column(Numeric(10, 2), nullable=False)
    payment_status = Column(String(30), nullable=False, default="pending")  # pending, paid, waived

    epoch = relationship("SettlementEpoch", back_populates="items")
    user = relationship("User", back_populates="settlement_items")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
