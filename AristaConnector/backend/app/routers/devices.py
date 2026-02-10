from datetime import datetime, timedelta
from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.events import get_event_stats, get_recent_events
from app.database import get_db
from app.models import Device, DeviceIdentity
from app.schemas import (
    ConnectionTestResponse,
    DeviceCreate,
    DeviceResponse,
    DeviceStatus,
    DeviceUpdate,
    EventResponse,
)
from app.services.device_identity import (
    IDENTITY_MODE_AUTO,
    IDENTITY_MODE_MANUAL,
    IDENTITY_STATUS_UNBOUND,
)
from app.services.eapi_client import test_connection
from app.services.redis_client import get_redis_client
from app.utils.encryption import encrypt_password
from app.utils.validation import validate_ip_address, validate_interval

router = APIRouter()


def _serialize_device(device: Device, identity: DeviceIdentity | None) -> dict[str, Any]:
    identity_mode = identity.mode if identity and identity.mode else IDENTITY_MODE_AUTO
    identity_status = identity.status if identity and identity.status else IDENTITY_STATUS_UNBOUND

    return {
        "id": device.id,
        "hostname": device.hostname,
        "ip": device.ip,
        "port": device.port,
        "username": device.username,
        "interval_sec": device.interval_sec,
        "enabled": device.enabled,
        "identity_mode": identity_mode,
        "identity_status": identity_status,
        "expected_identity_fingerprint": identity.expected_fingerprint if identity else None,
        "last_observed_identity_fingerprint": identity.last_observed_fingerprint if identity else None,
        "identity_last_verified_at": identity.last_verified_at if identity else None,
        "identity_last_conflict_at": identity.last_conflict_at if identity else None,
        "created_at": device.created_at,
        "updated_at": device.updated_at,
    }


async def _get_identity_map(db: AsyncSession, device_ids: list[UUID]) -> dict[UUID, DeviceIdentity]:
    if not device_ids:
        return {}

    result = await db.execute(select(DeviceIdentity).where(DeviceIdentity.device_id.in_(device_ids)))
    identities = result.scalars().all()
    return {identity.device_id: identity for identity in identities}


async def _get_or_create_identity(
    db: AsyncSession,
    device_id: UUID,
    *,
    default_mode: str = IDENTITY_MODE_AUTO,
    expected_fingerprint: str | None = None,
) -> DeviceIdentity:
    result = await db.execute(select(DeviceIdentity).where(DeviceIdentity.device_id == device_id))
    identity = result.scalar_one_or_none()
    if identity:
        return identity

    identity = DeviceIdentity(
        device_id=device_id,
        mode=default_mode,
        expected_fingerprint=expected_fingerprint,
        status=IDENTITY_STATUS_UNBOUND,
    )
    db.add(identity)
    await db.flush()
    return identity


async def _ensure_expected_fingerprint_unique(
    db: AsyncSession,
    expected_fingerprint: str | None,
    *,
    exclude_device_id: UUID | None = None,
) -> None:
    if not expected_fingerprint:
        return

    query = select(DeviceIdentity).where(DeviceIdentity.expected_fingerprint == expected_fingerprint)
    if exclude_device_id is not None:
        query = query.where(DeviceIdentity.device_id != exclude_device_id)

    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="expected_identity_fingerprint already assigned to another device",
        )


@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(device: DeviceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new device"""
    if not validate_ip_address(device.ip):
        raise HTTPException(status_code=400, detail="Invalid IP address format")

    if not validate_interval(device.interval_sec):
        raise HTTPException(status_code=400, detail="Interval must be between 5 and 300 seconds")

    result = await db.execute(select(Device).where(Device.ip == device.ip))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Device with this IP address already exists")

    identity_mode = device.identity_mode
    expected_fingerprint = device.expected_identity_fingerprint
    await _ensure_expected_fingerprint_unique(db, expected_fingerprint)

    password_enc = encrypt_password(device.password)
    device_data = device.model_dump(
        exclude={"password", "identity_mode", "expected_identity_fingerprint"},
    )
    device_data["password_enc"] = password_enc

    db_device = Device(**device_data)
    db.add(db_device)
    await db.flush()

    identity = DeviceIdentity(
        device_id=db_device.id,
        mode=identity_mode,
        expected_fingerprint=expected_fingerprint,
        status=IDENTITY_STATUS_UNBOUND,
    )
    db.add(identity)

    await db.commit()
    await db.refresh(db_device)
    await db.refresh(identity)
    return _serialize_device(db_device, identity)


@router.get("", response_model=List[DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db)):
    """List all devices"""
    result = await db.execute(select(Device).order_by(Device.created_at.desc()))
    devices = result.scalars().all()
    identities = await _get_identity_map(db, [device.id for device in devices])
    return [_serialize_device(device, identities.get(device.id)) for device in devices]


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific device"""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    identity = await _get_or_create_identity(db, device.id)
    await db.commit()
    return _serialize_device(device, identity)


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID,
    device_update: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a device (interval, enabled, credentials, identity settings, etc.)"""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    update_data = device_update.model_dump(exclude_unset=True)
    identity_mode = update_data.pop("identity_mode", None)
    expected_fp_provided = "expected_identity_fingerprint" in update_data
    expected_fingerprint = update_data.pop("expected_identity_fingerprint", None)

    if "password" in update_data:
        update_data["password_enc"] = encrypt_password(update_data.pop("password"))

    if "ip" in update_data and not validate_ip_address(update_data["ip"]):
        raise HTTPException(status_code=400, detail="Invalid IP address format")

    if "interval_sec" in update_data and not validate_interval(update_data["interval_sec"]):
        raise HTTPException(status_code=400, detail="Interval must be between 5 and 300 seconds")

    if "ip" in update_data and update_data["ip"] != device.ip:
        result = await db.execute(select(Device).where(Device.ip == update_data["ip"]))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Device with this IP address already exists")

    identity: DeviceIdentity | None = None
    if identity_mode is not None or expected_fp_provided:
        identity = await _get_or_create_identity(db, device.id)
        next_mode = identity_mode if identity_mode is not None else identity.mode
        next_mode = next_mode or IDENTITY_MODE_AUTO
        next_expected_fp = expected_fingerprint if expected_fp_provided else identity.expected_fingerprint

        if next_mode == IDENTITY_MODE_MANUAL and not next_expected_fp:
            raise HTTPException(
                status_code=422,
                detail="expected_identity_fingerprint is required when identity_mode=manual",
            )

        await _ensure_expected_fingerprint_unique(
            db,
            next_expected_fp,
            exclude_device_id=device.id,
        )

        mode_changed = identity.mode != next_mode
        expected_changed = expected_fp_provided and identity.expected_fingerprint != next_expected_fp

        if identity_mode is not None:
            identity.mode = next_mode
        if expected_fp_provided:
            identity.expected_fingerprint = next_expected_fp

        if mode_changed or expected_changed:
            identity.status = IDENTITY_STATUS_UNBOUND
            identity.last_verified_at = None
            identity.last_conflict_at = None

    for field, value in update_data.items():
        setattr(device, field, value)

    if identity is None:
        identity = await _get_or_create_identity(db, device.id)

    await db.commit()
    await db.refresh(device)
    await db.refresh(identity)
    return _serialize_device(device, identity)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a device by ID."""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    await db.delete(device)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{device_id}/test-connection", response_model=ConnectionTestResponse)
async def test_device_connection(device_id: UUID, db: AsyncSession = Depends(get_db)):
    """Test connection to device using eAPI 'show hostname' command"""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    success, message, hostname = await test_connection(
        ip=device.ip,
        port=device.port,
        username=device.username,
        password_enc=device.password_enc,
    )

    return ConnectionTestResponse(
        success=success,
        message=message,
        hostname=hostname,
    )


@router.get("/{device_id}/status", response_model=DeviceStatus)
async def get_device_status(device_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get device status from Redis with recent stats"""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    redis_client = await get_redis_client()
    last_seen_key = f"device:{device_id}:last_seen"
    status_key = f"device:{device_id}:status"

    last_seen_str = await redis_client.get(last_seen_key)
    status_raw = await redis_client.get(status_key)
    status_str = status_raw.decode() if status_raw else "unknown"

    last_seen = None
    if last_seen_str:
        try:
            last_seen = datetime.fromisoformat(last_seen_str.decode())
        except Exception:
            last_seen = None

    online = False
    if last_seen:
        age = (datetime.now() - last_seen).total_seconds()
        online = status_str == "online" and age <= 30

    since = datetime.now() - timedelta(hours=1)
    stats = await get_event_stats(db, device_id, since)
    recent_stats = {
        "total_events_last_hour": stats["total_events"],
        "events_by_type": stats["events_by_type"],
        "last_event_at": stats["last_event_at"].isoformat() if stats["last_event_at"] else None,
        "latency_ms": None,
    }

    latency_key = f"device:{device_id}:latency_ms"
    latency_str = await redis_client.get(latency_key)
    if latency_str:
        try:
            recent_stats["latency_ms"] = float(latency_str.decode())
        except Exception:
            pass

    return DeviceStatus(
        device_id=device_id,
        status=status_str,
        last_seen=last_seen,
        online=online,
        recent_stats=recent_stats,
    )


@router.get("/{device_id}/events", response_model=List[EventResponse])
async def get_device_events(
    device_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get recent events for a device"""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    events = await get_recent_events(db, device_id, limit=limit)

    import json

    result_events = []
    for event in events:
        metadata_obj = None
        if event.metadata_json:
            try:
                metadata_obj = json.loads(event.metadata_json)
            except Exception:
                metadata_obj = event.metadata_json

        result_events.append(
            EventResponse(
                id=event.id,
                device_id=event.device_id,
                event_type=event.event_type,
                message=event.message,
                metadata=metadata_obj,
                created_at=event.created_at,
            )
        )

    return result_events
