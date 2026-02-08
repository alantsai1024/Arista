from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Device
from app.schemas import FleetHealth, DeviceStatus, DeviceLatency
from app.services.redis_client import get_redis_client
from app.dao.events import get_event_stats

router = APIRouter()


@router.get("/fleet", response_model=FleetHealth)
async def get_fleet_health(db: AsyncSession = Depends(get_db)):
    """Get health status of all devices with summary counts and top latency devices"""
    result = await db.execute(select(Device))
    devices = result.scalars().all()

    redis_client = await get_redis_client()
    device_statuses = []
    online_count = 0
    offline_count = 0
    degraded_count = 0
    latency_devices = []

    for device in devices:
        last_seen_key = f"device:{device.id}:last_seen"
        status_key = f"device:{device.id}:status"
        latency_key = f"device:{device.id}:latency_ms"

        last_seen_str = await redis_client.get(last_seen_key)
        status = await redis_client.get(status_key)
        latency_str = await redis_client.get(latency_key)

        last_seen = None
        if last_seen_str:
            try:
                last_seen = datetime.fromisoformat(last_seen_str.decode())
            except:
                pass

        status_str = status.decode() if status else "unknown"
        
        # Determine online status (last_seen within 30s)
        online = False
        if last_seen:
            age = (datetime.now() - last_seen).total_seconds()
            online = age <= 30
        
        # Count by status
        if status_str == "online" and online:
            online_count += 1
        elif status_str == "degraded":
            degraded_count += 1
        else:
            offline_count += 1

        device_statuses.append(DeviceStatus(
            device_id=device.id,
            status=status_str,
            last_seen=last_seen,
            online=online
        ))
        
        # Collect latency data
        if latency_str:
            try:
                latency_ms = float(latency_str.decode())
                latency_devices.append(DeviceLatency(
                    device_id=device.id,
                    hostname=device.hostname,
                    ip=device.ip,
                    latency_ms=latency_ms
                ))
            except:
                pass

    # Sort by latency and get top 5
    latency_devices.sort(key=lambda x: x.latency_ms or float('inf'), reverse=True)
    top_latency = latency_devices[:5]

    return FleetHealth(
        total_devices=len(devices),
        online_devices=online_count,
        offline_devices=offline_count,
        degraded_devices=degraded_count,
        devices=device_statuses,
        top_latency_devices=top_latency
    )
