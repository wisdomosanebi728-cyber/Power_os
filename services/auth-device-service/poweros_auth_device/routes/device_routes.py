import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from poweros_common.models.entities import Device
from poweros_common.database import get_engine, get_session_factory
from poweros_common.schemas.auth import (
    DeviceProvisionRequest,
    DeviceProvisionResponse,
)
from poweros_common.security import (
    generate_device_token,
    hash_device_token,
)
from ..config import AuthDeviceConfig

logger = logging.getLogger("poweros-device")
router = APIRouter(prefix="/api/v1", tags=["Devices & Assets"])
config = AuthDeviceConfig()


def get_db(request: Request):
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        try:
            engine = get_engine(config.DATABASE_URL)
            session_factory = get_session_factory(engine)
            request.app.state.session_factory = session_factory
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database service temporarily unavailable: {str(e)}"
            )

    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@router.get("/communities/{community_id}/devices")
def list_community_devices(community_id: str, db: Session = Depends(get_db)):
    try:
        comm_uuid = uuid.UUID(community_id) if isinstance(community_id, str) else community_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid community UUID format")

    devices = db.query(Device).filter(Device.community_id == comm_uuid).all()
    return [
        {
            "id": d.id,
            "community_id": str(d.community_id),
            "device_type": d.device_type,
            "hardware_model": d.hardware_model,
            "capacity_kw": float(d.capacity_kw),
            "capacity_kwh": float(d.capacity_kwh) if d.capacity_kwh else None,
            "is_active": d.is_active,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in devices
    ]


@router.post("/communities/{community_id}/devices/provision", response_model=DeviceProvisionResponse, status_code=status.HTTP_201_CREATED)
def provision_device(community_id: str, req: DeviceProvisionRequest, db: Session = Depends(get_db)):
    existing = db.query(Device).filter(Device.id == req.device_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device ID already registered")

    try:
        comm_uuid = uuid.UUID(community_id) if isinstance(community_id, str) else community_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid community UUID format")

    raw_token = generate_device_token()
    token_hash = hash_device_token(raw_token)

    owner_uuid = None
    if req.owner_user_id:
        try:
            owner_uuid = uuid.UUID(req.owner_user_id) if isinstance(req.owner_user_id, str) else req.owner_user_id
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid owner user UUID format")

    new_device = Device(
        id=req.device_id,
        community_id=comm_uuid,
        owner_user_id=owner_uuid,
        device_type=req.device_type,
        hardware_model=req.hardware_model,
        auth_token_hash=token_hash,
        capacity_kw=req.capacity_kw,
        capacity_kwh=req.capacity_kwh or 0.0,
        is_active=True,
    )
    db.add(new_device)
    db.commit()

    topic = f"power-os/community/{community_id}/device/{req.device_id}/telemetry"

    return DeviceProvisionResponse(
        device_id=new_device.id,
        community_id=str(new_device.community_id),
        device_type=new_device.device_type,
        raw_auth_token=raw_token,
        mqtt_telemetry_topic=topic,
        created_at=new_device.created_at,
    )


@router.get("/devices/{device_id}")
def get_device(device_id: str, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {
        "id": device.id,
        "community_id": str(device.community_id),
        "device_type": device.device_type,
        "hardware_model": device.hardware_model,
        "capacity_kw": float(device.capacity_kw),
        "capacity_kwh": float(device.capacity_kwh) if device.capacity_kwh else None,
        "is_active": device.is_active,
        "created_at": device.created_at.isoformat() if device.created_at else None,
    }
