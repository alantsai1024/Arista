from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Device
from app.schemas import FleetHealth, DeviceStatus, DeviceLatency
from app.services.redis_client import get_redis_client
from app.dao.events import get_bulk_event_stats

router = APIRouter()


@router.get("/fleet", response_model=FleetHealth)
async def get_fleet_health(db: AsyncSession = Depends(get_db)):
    """Get health status of all devices with summary counts and top latency devices"""
    result = await db.execute(select(Device))
    devices = result.scalars().all()
    device_ids = [device.id for device in devices]

    redis_client = await get_redis_client()
    since = datetime.now() - timedelta(hours=1)
    event_stats_map = await get_bulk_event_stats(db, device_ids, since)

    last_seen_keys = [f"device:{device_id}:last_seen" for device_id in device_ids]
    status_keys = [f"device:{device_id}:status" for device_id in device_ids]
    latency_keys = [f"device:{device_id}:latency_ms" for device_id in device_ids]

    last_seen_values = await redis_client.mget(*last_seen_keys) if last_seen_keys else []
    status_values = await redis_client.mget(*status_keys) if status_keys else []
    latency_values = await redis_client.mget(*latency_keys) if latency_keys else []

    device_statuses = []
    online_count = 0
    offline_count = 0
    degraded_count = 0
    latency_devices = []

    for idx, device in enumerate(devices):
        last_seen_raw = last_seen_values[idx] if idx < len(last_seen_values) else None
        status_raw = status_values[idx] if idx < len(status_values) else None
        latency_raw = latency_values[idx] if idx < len(latency_values) else None

        last_seen = None
        if last_seen_raw:
            try:
                last_seen = datetime.fromisoformat(last_seen_raw.decode())
            except Exception:
                pass

        status_str = status_raw.decode() if status_raw else "unknown"
        
        # Determine online status (must be explicit online + fresh last_seen)
        online = False
        if last_seen:
            age = (datetime.now() - last_seen).total_seconds()
            online = status_str == "online" and age <= 30
        
        # Count by status
        if status_str == "online" and online:
            online_count += 1
        elif status_str == "degraded":
            degraded_count += 1
        else:
            offline_count += 1

        latency_ms = None
        if latency_raw:
            try:
                latency_ms = float(latency_raw.decode())
            except Exception:
                latency_ms = None

        stats = event_stats_map.get(device.id, {})
        last_event_at = stats.get("last_event_at")
        recent_stats = {
            "total_events_last_hour": stats.get("total_events", 0),
            "events_by_type": stats.get("events_by_type", {}),
            "last_event_at": last_event_at.isoformat() if last_event_at else None,
            "latency_ms": latency_ms,
        }

        device_statuses.append(DeviceStatus(
            device_id=device.id,
            status=status_str,
            last_seen=last_seen,
            online=online,
            recent_stats=recent_stats,
        ))
        
        # Collect latency data
        if latency_ms is not None:
            latency_devices.append(DeviceLatency(
                device_id=device.id,
                hostname=device.hostname,
                ip=device.ip,
                latency_ms=latency_ms
            ))

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
