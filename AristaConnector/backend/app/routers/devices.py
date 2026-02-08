from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import Device
from app.schemas import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceStatus,
    ConnectionTestResponse,
    EventResponse
)
from app.services.redis_client import get_redis_client
from app.services.eapi_client import test_connection
from app.utils.encryption import encrypt_password
from app.utils.validation import validate_ip_address, validate_interval
from app.dao.events import get_event_stats, get_recent_events

router = APIRouter()


@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(device: DeviceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new device"""
    # Validate IP address
    if not validate_ip_address(device.ip):
        raise HTTPException(status_code=400, detail="Invalid IP address format")
    
    # Validate interval
    if not validate_interval(device.interval_sec):
        raise HTTPException(status_code=400, detail="Interval must be between 5 and 300 seconds")
    
    # Check if device with same IP already exists
    result = await db.execute(select(Device).where(Device.ip == device.ip))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Device with this IP address already exists")
    
    # Encrypt password
    password_enc = encrypt_password(device.password)
    
    # Create device (exclude password from model_dump, use encrypted version)
    device_data = device.model_dump(exclude={'password'})
    device_data['password_enc'] = password_enc
    
    db_device = Device(**device_data)
    db.add(db_device)
    await db.commit()
    await db.refresh(db_device)
    return db_device


@router.get("", response_model=List[DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db)):
    """List all devices"""
    result = await db.execute(select(Device).order_by(Device.created_at.desc()))
    devices = result.scalars().all()
    return devices


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific device"""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID,
    device_update: DeviceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a device (interval, enabled, credentials, etc.)"""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    update_data = device_update.model_dump(exclude_unset=True)
    
    # Handle password encryption if provided
    if 'password' in update_data:
        update_data['password_enc'] = encrypt_password(update_data.pop('password'))
    
    # Validate IP if provided
    if 'ip' in update_data and not validate_ip_address(update_data['ip']):
        raise HTTPException(status_code=400, detail="Invalid IP address format")
    
    # Validate interval if provided
    if 'interval_sec' in update_data and not validate_interval(update_data['interval_sec']):
        raise HTTPException(status_code=400, detail="Interval must be between 5 and 300 seconds")
    
    # Check IP uniqueness if IP is being updated
    if 'ip' in update_data and update_data['ip'] != device.ip:
        result = await db.execute(select(Device).where(Device.ip == update_data['ip']))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Device with this IP address already exists")
    
    # Update fields
    for field, value in update_data.items():
        setattr(device, field, value)
    
    await db.commit()
    await db.refresh(device)
    return device


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
    
    # Test connection
    success, message, hostname = await test_connection(
        ip=device.ip,
        port=device.port,
        username=device.username,
        password_enc=device.password_enc
    )
    
    return ConnectionTestResponse(
        success=success,
        message=message,
        hostname=hostname
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
    status = await redis_client.get(status_key)
    
    from datetime import datetime, timedelta
    last_seen = None
    if last_seen_str:
        try:
            last_seen = datetime.fromisoformat(last_seen_str.decode())
        except:
            pass
    
    # Determine online status (last_seen within 30s)
    online = False
    if last_seen:
        age = (datetime.now() - last_seen).total_seconds()
        online = age <= 30
    
    # Get recent event stats (last hour)
    since = datetime.now() - timedelta(hours=1)
    stats = await get_event_stats(db, device_id, since)
    
    # Build recent stats
    recent_stats = {
        "total_events_last_hour": stats["total_events"],
        "events_by_type": stats["events_by_type"],
        "last_event_at": stats["last_event_at"].isoformat() if stats["last_event_at"] else None,
        "latency_ms": None
    }
    
    # Get latency from Redis
    latency_key = f"device:{device_id}:latency_ms"
    latency_str = await redis_client.get(latency_key)
    if latency_str:
        try:
            recent_stats["latency_ms"] = float(latency_str.decode())
        except:
            pass
    
    return DeviceStatus(
        device_id=device_id,
        status=status.decode() if status else "unknown",
        last_seen=last_seen,
        online=online,
        recent_stats=recent_stats
    )


@router.get("/{device_id}/events", response_model=List[EventResponse])
async def get_device_events(
    device_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get recent events for a device"""
    # Verify device exists
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get events
    events = await get_recent_events(db, device_id, limit=limit)
    
    # Parse metadata JSON strings
    import json
    result_events = []
    for event in events:
        metadata_obj = None
        if event.metadata_json:
            try:
                metadata_obj = json.loads(event.metadata_json)
            except:
                metadata_obj = event.metadata_json
        
        result_events.append(EventResponse(
            id=event.id,
            device_id=event.device_id,
            event_type=event.event_type,
            message=event.message,
            metadata=metadata_obj,
            created_at=event.created_at
        ))
    
    return result_events
