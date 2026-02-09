"""
Data Access Object for events.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
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
    summary_query = select(
        func.count(Event.id),
        func.max(Event.created_at),
    ).where(Event.device_id == device_id)

    grouped_query = select(
        Event.event_type,
        func.count(Event.id),
    ).where(Event.device_id == device_id)

    if since:
        summary_query = summary_query.where(Event.created_at >= since)
        grouped_query = grouped_query.where(Event.created_at >= since)

    grouped_query = grouped_query.group_by(Event.event_type)

    summary_result = await db.execute(summary_query)
    total_events, last_event_at = summary_result.one()

    grouped_result = await db.execute(grouped_query)
    by_type = {event_type: int(count) for event_type, count in grouped_result.all()}

    return {
        "total_events": int(total_events or 0),
        "events_by_type": by_type,
        "last_event_at": last_event_at,
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

    summary_query = select(
        Event.device_id,
        func.count(Event.id),
        func.max(Event.created_at),
    ).where(Event.device_id.in_(device_ids))
    grouped_query = select(
        Event.device_id,
        Event.event_type,
        func.count(Event.id),
    ).where(Event.device_id.in_(device_ids))

    if since:
        summary_query = summary_query.where(Event.created_at >= since)
        grouped_query = grouped_query.where(Event.created_at >= since)

    summary_query = summary_query.group_by(Event.device_id)
    grouped_query = grouped_query.group_by(Event.device_id, Event.event_type)

    summary_rows = (await db.execute(summary_query)).all()
    grouped_rows = (await db.execute(grouped_query)).all()

    stats: dict[UUID, dict] = {}
    for device_id, total_events, last_event_at in summary_rows:
        device_stats = stats.setdefault(
            device_id,
            {
                "total_events": int(total_events or 0),
                "events_by_type": {},
                "last_event_at": last_event_at,
            },
        )

    for device_id, event_type, count in grouped_rows:
        device_stats = stats.setdefault(
            device_id,
            {
                "total_events": 0,
                "events_by_type": {},
                "last_event_at": None,
            },
        )
        by_type = device_stats["events_by_type"]
        by_type[event_type] = int(count)

    return stats
