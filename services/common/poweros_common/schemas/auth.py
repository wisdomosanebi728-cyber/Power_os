from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    OPERATOR = "operator"
    ADMIN = "admin"
    CONSUMER = "consumer"
    AUDITOR = "auditor"


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    role: UserRole = UserRole.CONSUMER
    community_id: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    community_id: Optional[str] = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class DeviceProvisionRequest(BaseModel):
    device_id: str = Field(..., min_length=3, max_length=64)
    device_type: str = Field(..., description="solar_inverter, battery_storage, generator, grid_meter, consumer_meter")
    hardware_model: Optional[str] = None
    capacity_kw: float = Field(0.0, ge=0.0)
    capacity_kwh: Optional[float] = Field(0.0, ge=0.0)
    owner_user_id: Optional[str] = None


class DeviceProvisionResponse(BaseModel):
    device_id: str
    community_id: str
    device_type: str
    raw_auth_token: str
    mqtt_telemetry_topic: str
    created_at: datetime
