"""
Data Access Object for events.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.models import Event


async def create_event(
    db: AsyncSession,
    device_id: UUID,
    event_type: str,
    message: Optional[str] = None,
    metadata: Optional[dict] = None
) -> Event:
    """
    Create a new event.
    
    Args:
        db: Database session
        device_id: Device UUID
        event_type: Type of event (e.g., 'poll_success', 'poll_error', 'device_online', 'device_offline')
        message: Event message
        metadata: Additional metadata as dict (will be stored as JSON string)
        
    Returns:
        Created Event object
    """
    import json
    
    event = Event(
        device_id=device_id,
        event_type=event_type,
        message=message,
        metadata_json=json.dumps(metadata) if metadata else None
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def get_recent_events(
    db: AsyncSession,
    device_id: UUID,
    limit: int = 10,
    event_type: Optional[str] = None
) -> List[Event]:
    """
    Get recent events for a device.
    
    Args:
        db: Database session
        device_id: Device UUID
        limit: Maximum number of events to return
        event_type: Optional filter by event type
        
    Returns:
        List of Event objects
    """
    query = select(Event).where(Event.device_id == device_id)
    
    if event_type:
        query = query.where(Event.event_type == event_type)
    
    query = query.order_by(desc(Event.created_at)).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_event_stats(
    db: AsyncSession,
    device_id: UUID,
    since: Optional[datetime] = None
) -> dict:
    """
    Get event statistics for a device.
    
    Args:
        db: Database session
        device_id: Device UUID
        since: Optional datetime to filter events since
        
    Returns:
        Dictionary with event statistics
    """
    query = select(Event).where(Event.device_id == device_id)
    
    if since:
        query = query.where(Event.created_at >= since)
    
    query = query.order_by(desc(Event.created_at))

    result = await db.execute(query)
    events = result.scalars().all()
    
    total = len(events)
    by_type = {}
    for event in events:
        by_type[event.event_type] = by_type.get(event.event_type, 0) + 1
    
    return {
        "total_events": total,
        "events_by_type": by_type,
        "last_event_at": events[0].created_at if events else None
    }


async def get_bulk_event_stats(
    db: AsyncSession,
    device_ids: list[UUID],
    since: Optional[datetime] = None,
) -> dict[UUID, dict]:
    """
    Get event statistics for multiple devices in one query.

    Returns:
        Mapping of device_id -> {
            total_events: int,
            events_by_type: dict[str, int],
            last_event_at: datetime | None
        }
    """
    if not device_ids:
        return {}

    query = select(Event.device_id, Event.event_type, Event.created_at).where(Event.device_id.in_(device_ids))
    if since:
        query = query.where(Event.created_at >= since)

    result = await db.execute(query)
    rows = result.all()

    stats: dict[UUID, dict] = {}
    for device_id, event_type, created_at in rows:
        device_stats = stats.setdefault(
            device_id,
            {
                "total_events": 0,
                "events_by_type": {},
                "last_event_at": None,
            },
        )
        device_stats["total_events"] += 1
        by_type = device_stats["events_by_type"]
        by_type[event_type] = by_type.get(event_type, 0) + 1

        current_last = device_stats["last_event_at"]
        if current_last is None or created_at > current_last:
            device_stats["last_event_at"] = created_at

    return stats
