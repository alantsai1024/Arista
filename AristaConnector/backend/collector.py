"""
Arista Device Collector Service

Polls enabled devices at configured intervals using eAPI.
Implements concurrency control, exponential backoff, health tracking,
optional poctest-compatible raw MQTT publishing, and local raw retention.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from uuid import UUID

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.dao.events import create_event
from app.models import Device
from app.services.collector_client import calculate_backoff_delay, poll_device
from app.services.collector_profile import get_raw_topic_for_command
from app.services.mqtt_client import (
    get_collector_name,
    publish_raw_compat,
    publish_state,
    publish_telemetry,
)
from app.services.redis_client import close_redis_client, get_redis_client
from app.services.retention_sink import RetentionSink

# Load environment variables
load_dotenv()

# Database setup
database_url = os.getenv("DATABASE_URL", "postgresql://arista:arista123@localhost:5432/arista")
parsed = urlparse(database_url)
if parsed.scheme == "postgresql":
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Configuration
POLLING_TIMEOUT = float(os.getenv("POLLING_TIMEOUT", "5.0"))
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_POLLS", "20"))
OFFLINE_THRESHOLD_SEC = int(os.getenv("OFFLINE_THRESHOLD_SEC", "30"))

# Retention configuration
RETENTION_ENABLED = os.getenv("RETENTION_ENABLED", "true").lower() in ("1", "true", "yes")
RETENTION_BASE_DIR = os.getenv("RETENTION_BASE_DIR", "./runtime")
RETENTION_TARGETS_RAW = os.getenv("RETENTION_TARGETS", "*")
RETENTION_LOG_PATH = os.getenv("RETENTION_LOG_PATH", "")
RETENTION_TARGETS = {x.strip() for x in RETENTION_TARGETS_RAW.split(",") if x.strip()}

# Per-device state tracking
device_states: Dict[UUID, Dict] = {}


def build_retention_sink() -> RetentionSink:
    return RetentionSink(
        base_dir=RETENTION_BASE_DIR,
        enabled=RETENTION_ENABLED,
        targets=RETENTION_TARGETS if RETENTION_TARGETS else None,
        log_jsonl_path=RETENTION_LOG_PATH or None,
    )


async def get_enabled_devices(db: AsyncSession) -> list[Device]:
    """Get all enabled devices from database."""
    result = await db.execute(select(Device).where(Device.enabled == True))  # noqa: E712
    return result.scalars().all()


async def update_redis_health(device_id: UUID, status: str, redis_client, latency_ms: Optional[float] = None) -> None:
    """Update Redis with device health information."""
    now = datetime.now()
    now_str = now.isoformat()

    await redis_client.setex(f"device:{device_id}:last_seen", 60, now_str)
    await redis_client.set(f"device:{device_id}:status", status)

    if latency_ms is not None:
        await redis_client.set(f"device:{device_id}:latency_ms", str(latency_ms))


def get_device_status(device_id: UUID, last_seen: Optional[datetime]) -> str:
    """
    Determine device status based on last_seen.
    """
    if last_seen is None:
        return "offline"

    age = (datetime.now() - last_seen).total_seconds()
    if age > OFFLINE_THRESHOLD_SEC:
        return "offline"

    return "online"


async def record_event(
    event_session_factory: async_sessionmaker[AsyncSession],
    *,
    device_id: UUID,
    event_type: str,
    message: str,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Persist one event using an isolated DB session.

    Poll tasks run concurrently, so each write must use a separate session.
    """
    try:
        async with event_session_factory() as event_db:
            await create_event(
                db=event_db,
                device_id=device_id,
                event_type=event_type,
                message=message,
                metadata=metadata,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Event persist failed for {device_id} ({event_type}): {exc}")


def persist_raw_evidence(
    sink: RetentionSink,
    *,
    device_identifier: str,
    command: str,
    raw_result,
    ts: int,
) -> None:
    """
    Persist one command result to local raw/raw_ref folders.
    Any error is logged and swallowed.
    """
    collector_name = get_collector_name(command)
    topic = get_raw_topic_for_command(command)
    payload = {
        "device": device_identifier,
        "collector": collector_name,
        "cmds": [command],
        "format": "json",
        "raw": [raw_result],
        "ts": ts,
    }
    result = sink.persist(topic=topic, payload=payload)
    if not result.get("ok"):
        print(f"⚠ Retention persist failed ({collector_name}): {result.get('error', 'unknown error')}")

    sink.log_event(
        {
            "device": device_identifier,
            "collector": collector_name,
            "cmds": [command],
            "topic": topic,
            "ts": ts,
            "retention_ok": bool(result.get("ok")),
            "retention_skipped": bool(result.get("skipped", False)),
            "raw_file": result.get("raw_file"),
            "ref_file": result.get("ref_file"),
            "error": result.get("error"),
        }
    )


async def poll_single_device(
    device: Device,
    semaphore: asyncio.Semaphore,
    redis_client,
    sink: RetentionSink,
    event_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """
    Poll a single device with error handling and backoff.
    """
    async with semaphore:
        device_id = device.id

        if device_id not in device_states:
            device_states[device_id] = {
                "error_count": 0,
                "last_poll_time": None,
                "last_success_time": None,
            }

        state = device_states[device_id]
        now = datetime.now()

        if state["error_count"] > 0:
            backoff_delay = calculate_backoff_delay(state["error_count"])
            last_error_time = state.get("last_error_time")
            if last_error_time:
                time_since_error = (now - last_error_time).total_seconds()
                if time_since_error < backoff_delay:
                    return

        try:
            success, error_msg, data, latency_ms = await poll_device(
                ip=device.ip,
                port=device.port,
                username=device.username,
                password_enc=device.password_enc,
                timeout=POLLING_TIMEOUT,
            )

            state["last_poll_time"] = now

            if success:
                state["error_count"] = 0
                state["last_success_time"] = now

                await update_redis_health(device_id, "online", redis_client, latency_ms)

                await record_event(
                    event_session_factory,
                    device_id=device_id,
                    event_type="poll_success",
                    message="Device polled successfully",
                    metadata={
                        "commands": list(data.keys()) if data else [],
                        "hostname": data.get("show hostname", {}).get("hostname") if data else None,
                    },
                )

                hostname = data.get("show hostname", {}).get("hostname") if data else device.hostname
                publish_state(
                    device_id=device_id,
                    hostname=hostname,
                    ip=device.ip,
                    status="ok",
                    data={"status": "online", "last_seen": now.isoformat()},
                    duration_ms=latency_ms,
                )

                ts = int(now.timestamp())
                device_identifier = hostname or device.ip

                if data:
                    for cmd, result in data.items():
                        collector_name = get_collector_name(cmd)
                        publish_telemetry(
                            device_id=device_id,
                            hostname=hostname,
                            ip=device.ip,
                            collector=collector_name,
                            command=cmd,
                            data=result,
                            duration_ms=latency_ms,
                            status="ok",
                        )

                        publish_raw_compat(
                            device_identifier=device_identifier,
                            command=cmd,
                            raw_result=result,
                            ts=ts,
                        )

                        persist_raw_evidence(
                            sink,
                            device_identifier=device_identifier,
                            command=cmd,
                            raw_result=result,
                            ts=ts,
                        )

                print(f"✓ Device {device.hostname or device.ip} ({device_id}) - online")

            else:
                state["error_count"] += 1
                state["last_error_time"] = now

                status = "offline" if state["error_count"] >= 3 else "degraded"
                await update_redis_health(device_id, status, redis_client)

                await record_event(
                    event_session_factory,
                    device_id=device_id,
                    event_type="poll_error",
                    message=f"Poll failed: {error_msg}",
                    metadata={"error": error_msg, "error_count": state["error_count"]},
                )

                publish_state(
                    device_id=device_id,
                    hostname=device.hostname,
                    ip=device.ip,
                    status="error",
                    data={"status": status, "error": error_msg},
                )

                print(f"✗ Device {device.hostname or device.ip} ({device_id}) - {status}: {error_msg}")

        except Exception as exc:  # noqa: BLE001
            state["error_count"] += 1
            state["last_error_time"] = now

            await update_redis_health(device_id, "offline", redis_client)

            await record_event(
                event_session_factory,
                device_id=device_id,
                event_type="poll_error",
                message=f"Unexpected error: {str(exc)}",
                metadata={"error": str(exc), "error_count": state["error_count"]},
            )

            print(f"✗ Device {device.hostname or device.ip} ({device_id}) - error: {str(exc)}")


async def collector_loop() -> None:
    """Main collector loop."""
    print("Starting Arista Collector")
    print(f"  Max concurrent polls: {MAX_CONCURRENT}")
    print(f"  Polling timeout: {POLLING_TIMEOUT}s")
    print(f"  Offline threshold: {OFFLINE_THRESHOLD_SEC}s")
    print(f"  Retention enabled: {RETENTION_ENABLED}")
    print(f"  Retention base dir: {RETENTION_BASE_DIR}")

    redis_client = await get_redis_client()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    sink = build_retention_sink()

    try:
        while True:
            try:
                async with AsyncSessionLocal() as db:
                    devices = await get_enabled_devices(db)

                    if not devices:
                        print("No enabled devices found")
                        await asyncio.sleep(10)
                        continue

                    print(f"\nPolling {len(devices)} device(s)...")

                    tasks = []
                    for device in devices:
                        device_id = device.id
                        state = device_states.get(device_id, {})
                        last_poll = state.get("last_poll_time")

                        if last_poll:
                            time_since_poll = (datetime.now() - last_poll).total_seconds()
                            if time_since_poll < device.interval_sec:
                                continue

                        task = poll_single_device(
                            device,
                            semaphore,
                            redis_client,
                            sink,
                            AsyncSessionLocal,
                        )
                        tasks.append(task)

                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)

                await asyncio.sleep(5)
            except Exception as exc:  # noqa: BLE001
                print(f"⚠ Collector loop error: {exc}")
                await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("\nShutting down collector...")
    finally:
        await close_redis_client()
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(collector_loop())
    except KeyboardInterrupt:
        print("\nCollector stopped")
        sys.exit(0)
