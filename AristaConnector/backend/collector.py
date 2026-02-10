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
from app.models import Device, DeviceIdentity
from app.services.collector_client import calculate_backoff_delay, poll_device
from app.services.collector_profile import get_raw_topic_for_command
from app.services.device_identity import (
    IDENTITY_MODE_AUTO,
    IDENTITY_MODE_MANUAL,
    IDENTITY_STATUS_CONFLICT,
    IDENTITY_STATUS_INSUFFICIENT,
    IDENTITY_STATUS_UNBOUND,
    IDENTITY_STATUS_VERIFIED,
    extract_identity_observation,
)
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
MAX_CONSECUTIVE_ERROR_EVENT_WRITES = 4
MAX_CONSECUTIVE_IDENTITY_CONFLICT_EVENT_WRITES = 4
IDENTITY_ENFORCEMENT_MODE = os.getenv("IDENTITY_ENFORCEMENT_MODE", "strict").strip().lower()

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


async def record_poll_error_with_cap(
    event_session_factory: async_sessionmaker[AsyncSession],
    *,
    device_id: UUID,
    message: str,
    metadata: dict[str, Any],
    state: dict[str, Any],
) -> None:
    """
    Cap poll_error writes per consecutive failure streak.
    """
    write_count = int(state.get("consecutive_error_event_writes", 0))
    if write_count >= MAX_CONSECUTIVE_ERROR_EVENT_WRITES:
        if not state.get("error_event_suppressed", False):
            print(
                f"⚠ Device {device_id} poll_error writes capped at "
                f"{MAX_CONSECUTIVE_ERROR_EVENT_WRITES}; suppressing further writes until recovery"
            )
            state["error_event_suppressed"] = True
        return

    await record_event(
        event_session_factory,
        device_id=device_id,
        event_type="poll_error",
        message=message,
        metadata=metadata,
    )
    state["consecutive_error_event_writes"] = write_count + 1
    state["error_event_suppressed"] = (
        state["consecutive_error_event_writes"] >= MAX_CONSECUTIVE_ERROR_EVENT_WRITES
    )


def _is_identity_conflict_enforced() -> bool:
    return IDENTITY_ENFORCEMENT_MODE != "warn"


async def _get_or_create_device_identity(
    db: AsyncSession,
    *,
    device_id: UUID,
) -> DeviceIdentity:
    result = await db.execute(select(DeviceIdentity).where(DeviceIdentity.device_id == device_id))
    identity = result.scalar_one_or_none()
    if identity:
        return identity

    identity = DeviceIdentity(
        device_id=device_id,
        mode=IDENTITY_MODE_AUTO,
        status=IDENTITY_STATUS_UNBOUND,
    )
    db.add(identity)
    await db.flush()
    return identity


async def _resolve_identity(
    event_session_factory: async_sessionmaker[AsyncSession],
    *,
    device_id: UUID,
    data: Optional[dict[str, Any]],
) -> dict[str, Any]:
    observation = extract_identity_observation(data)
    now = datetime.now()
    conflict_enforced = _is_identity_conflict_enforced()

    async with event_session_factory() as event_db:
        identity = await _get_or_create_device_identity(event_db, device_id=device_id)
        mode = identity.mode or IDENTITY_MODE_AUTO

        identity.last_observed_fingerprint = observation.fingerprint
        identity.serial_number = observation.serial_number
        identity.system_mac = observation.system_mac
        identity.source = observation.source

        result_payload = {
            "mode": mode,
            "expected_fingerprint": identity.expected_fingerprint,
            "observed_fingerprint": observation.fingerprint,
            "serial_number": observation.serial_number,
            "system_mac": observation.system_mac,
            "source": observation.source,
            "identity_status": identity.status or IDENTITY_STATUS_UNBOUND,
            "event_type": None,
            "event_message": None,
            "event_metadata": None,
            "operational_status": "online",
            "allow_publish": True,
        }

        if observation.is_insufficient:
            identity.status = IDENTITY_STATUS_INSUFFICIENT
            await event_db.commit()

            result_payload.update(
                {
                    "identity_status": IDENTITY_STATUS_INSUFFICIENT,
                    "event_type": "identity_insufficient",
                    "event_message": "Device identity cannot be verified from show version",
                    "event_metadata": {
                        "source": observation.source,
                        "reason": "missing serialNumber and systemMacAddress",
                    },
                    "operational_status": "degraded",
                    "allow_publish": False,
                }
            )
            return result_payload

        expected_fp = identity.expected_fingerprint
        observed_fp = observation.fingerprint

        # First successful observation in auto mode binds expected fingerprint.
        if not expected_fp and mode == IDENTITY_MODE_AUTO:
            duplicate_query = select(DeviceIdentity).where(
                DeviceIdentity.expected_fingerprint == observed_fp,
                DeviceIdentity.device_id != device_id,
            )
            duplicate_result = await event_db.execute(duplicate_query)
            duplicate_identity = duplicate_result.scalar_one_or_none()

            if duplicate_identity is None:
                identity.expected_fingerprint = observed_fp
                identity.status = IDENTITY_STATUS_VERIFIED
                identity.last_verified_at = now
                await event_db.commit()

                result_payload.update(
                    {
                        "expected_fingerprint": observed_fp,
                        "identity_status": IDENTITY_STATUS_VERIFIED,
                        "event_type": "identity_bound",
                        "event_message": "Device identity bound from first successful poll",
                        "event_metadata": {
                            "mode": mode,
                            "source": observation.source,
                            "expected_fingerprint": observed_fp,
                            "serial_number": observation.serial_number,
                            "system_mac": observation.system_mac,
                        },
                    }
                )
                return result_payload

            identity.status = IDENTITY_STATUS_CONFLICT
            identity.last_conflict_at = now
            await event_db.commit()

            result_payload.update(
                {
                    "identity_status": IDENTITY_STATUS_CONFLICT,
                    "event_type": "identity_conflict",
                    "event_message": "Observed identity fingerprint conflicts with another device binding",
                    "event_metadata": {
                        "mode": mode,
                        "expected_fingerprint": expected_fp,
                        "observed_fingerprint": observed_fp,
                        "source": observation.source,
                        "reason": "observed fingerprint already bound to another device",
                        "conflicting_device_id": str(duplicate_identity.device_id),
                        "conflict_enforced": conflict_enforced,
                    },
                    "operational_status": "ip_conflict" if conflict_enforced else "online",
                    "allow_publish": not conflict_enforced,
                }
            )
            return result_payload

        if mode == IDENTITY_MODE_MANUAL and not expected_fp:
            identity.status = IDENTITY_STATUS_CONFLICT
            identity.last_conflict_at = now
            await event_db.commit()

            result_payload.update(
                {
                    "identity_status": IDENTITY_STATUS_CONFLICT,
                    "event_type": "identity_conflict",
                    "event_message": "Manual identity mode is missing expected fingerprint",
                    "event_metadata": {
                        "mode": mode,
                        "expected_fingerprint": expected_fp,
                        "observed_fingerprint": observed_fp,
                        "source": observation.source,
                        "reason": "manual mode without expected fingerprint",
                        "conflict_enforced": conflict_enforced,
                    },
                    "operational_status": "ip_conflict" if conflict_enforced else "online",
                    "allow_publish": not conflict_enforced,
                }
            )
            return result_payload

        if expected_fp == observed_fp:
            identity.status = IDENTITY_STATUS_VERIFIED
            identity.last_verified_at = now
            await event_db.commit()

            result_payload.update(
                {
                    "identity_status": IDENTITY_STATUS_VERIFIED,
                    "expected_fingerprint": expected_fp,
                }
            )
            return result_payload

        identity.status = IDENTITY_STATUS_CONFLICT
        identity.last_conflict_at = now
        await event_db.commit()

        result_payload.update(
            {
                "identity_status": IDENTITY_STATUS_CONFLICT,
                "event_type": "identity_conflict",
                "event_message": "Observed device fingerprint does not match expected identity",
                "event_metadata": {
                    "mode": mode,
                    "expected_fingerprint": expected_fp,
                    "observed_fingerprint": observed_fp,
                    "source": observation.source,
                    "reason": "fingerprint_mismatch",
                    "conflict_enforced": conflict_enforced,
                },
                "operational_status": "ip_conflict" if conflict_enforced else "online",
                "allow_publish": not conflict_enforced,
            }
        )
        return result_payload


async def record_identity_conflict_with_cap(
    event_session_factory: async_sessionmaker[AsyncSession],
    *,
    device_id: UUID,
    message: str,
    metadata: dict[str, Any],
    state: dict[str, Any],
) -> None:
    write_count = int(state.get("consecutive_identity_conflict_event_writes", 0))
    if write_count >= MAX_CONSECUTIVE_IDENTITY_CONFLICT_EVENT_WRITES:
        if not state.get("identity_conflict_event_suppressed", False):
            print(
                f"⚠ Device {device_id} identity_conflict writes capped at "
                f"{MAX_CONSECUTIVE_IDENTITY_CONFLICT_EVENT_WRITES}; suppressing further writes until recovery"
            )
            state["identity_conflict_event_suppressed"] = True
        return

    await record_event(
        event_session_factory,
        device_id=device_id,
        event_type="identity_conflict",
        message=message,
        metadata=metadata,
    )
    state["consecutive_identity_conflict_event_writes"] = write_count + 1
    state["identity_conflict_event_suppressed"] = (
        state["consecutive_identity_conflict_event_writes"] >= MAX_CONSECUTIVE_IDENTITY_CONFLICT_EVENT_WRITES
    )


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
                "consecutive_error_event_writes": 0,
                "error_event_suppressed": False,
                "consecutive_identity_conflict_event_writes": 0,
                "identity_conflict_event_suppressed": False,
                "last_identity_status": None,
            }

        state = device_states[device_id]
        state.setdefault("consecutive_error_event_writes", 0)
        state.setdefault("error_event_suppressed", False)
        state.setdefault("consecutive_identity_conflict_event_writes", 0)
        state.setdefault("identity_conflict_event_suppressed", False)
        state.setdefault("last_identity_status", None)
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
                state["consecutive_error_event_writes"] = 0
                state["error_event_suppressed"] = False
                previous_identity_status = state.get("last_identity_status")
                identity_result = await _resolve_identity(
                    event_session_factory,
                    device_id=device_id,
                    data=data,
                )
                identity_status = identity_result["identity_status"]
                state["last_identity_status"] = identity_status

                if identity_status == IDENTITY_STATUS_CONFLICT:
                    await record_identity_conflict_with_cap(
                        event_session_factory,
                        device_id=device_id,
                        message=identity_result["event_message"] or "Identity conflict detected",
                        metadata=identity_result["event_metadata"] or {},
                        state=state,
                    )
                else:
                    state["consecutive_identity_conflict_event_writes"] = 0
                    state["identity_conflict_event_suppressed"] = False

                if identity_result["event_type"] == "identity_bound":
                    await record_event(
                        event_session_factory,
                        device_id=device_id,
                        event_type="identity_bound",
                        message=identity_result["event_message"] or "Device identity bound",
                        metadata=identity_result["event_metadata"],
                    )
                elif (
                    identity_result["event_type"] == "identity_insufficient"
                    and previous_identity_status != IDENTITY_STATUS_INSUFFICIENT
                ):
                    await record_event(
                        event_session_factory,
                        device_id=device_id,
                        event_type="identity_insufficient",
                        message=identity_result["event_message"] or "Insufficient device identity",
                        metadata=identity_result["event_metadata"],
                    )

                hostname = data.get("show hostname", {}).get("hostname") if data else device.hostname
                operational_status = identity_result["operational_status"]

                if operational_status == "online":
                    await update_redis_health(device_id, "online", redis_client, latency_ms)

                    await record_event(
                        event_session_factory,
                        device_id=device_id,
                        event_type="poll_success",
                        message="Device polled successfully",
                        metadata={
                            "commands": list(data.keys()) if data else [],
                            "hostname": hostname,
                            "identity_status": identity_status,
                            "expected_fingerprint": identity_result.get("expected_fingerprint"),
                            "observed_fingerprint": identity_result.get("observed_fingerprint"),
                        },
                    )

                    envelope_status = "warning" if identity_status == IDENTITY_STATUS_CONFLICT else "ok"
                    publish_state(
                        device_id=device_id,
                        hostname=hostname,
                        ip=device.ip,
                        status=envelope_status,
                        data={
                            "status": "online",
                            "last_seen": now.isoformat(),
                            "identity_status": identity_status,
                            "expected_fingerprint": identity_result.get("expected_fingerprint"),
                            "observed_fingerprint": identity_result.get("observed_fingerprint"),
                        },
                        duration_ms=latency_ms,
                    )

                    ts = int(now.timestamp())
                    device_identifier = hostname or device.ip

                    if data and identity_result["allow_publish"]:
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

                    print(
                        f"✓ Device {device.hostname or device.ip} ({device_id}) - online "
                        f"[identity={identity_status}]"
                    )
                else:
                    await update_redis_health(device_id, operational_status, redis_client, latency_ms)

                    publish_state(
                        device_id=device_id,
                        hostname=hostname,
                        ip=device.ip,
                        status="error",
                        data={
                            "status": operational_status,
                            "identity_status": identity_status,
                            "expected_fingerprint": identity_result.get("expected_fingerprint"),
                            "observed_fingerprint": identity_result.get("observed_fingerprint"),
                            "source": identity_result.get("source"),
                        },
                        duration_ms=latency_ms,
                    )

                    print(
                        f"✗ Device {device.hostname or device.ip} ({device_id}) - "
                        f"{operational_status}: identity {identity_status}"
                    )

            else:
                state["error_count"] += 1
                state["last_error_time"] = now

                status = "offline" if state["error_count"] >= 3 else "degraded"
                await update_redis_health(device_id, status, redis_client)

                await record_poll_error_with_cap(
                    event_session_factory,
                    device_id=device_id,
                    message=f"Poll failed: {error_msg}",
                    metadata={
                        "error": error_msg,
                        "error_count": state["error_count"],
                        "consecutive_error_event_writes": state["consecutive_error_event_writes"],
                    },
                    state=state,
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

            await record_poll_error_with_cap(
                event_session_factory,
                device_id=device_id,
                message=f"Unexpected error: {str(exc)}",
                metadata={
                    "error": str(exc),
                    "error_count": state["error_count"],
                    "consecutive_error_event_writes": state["consecutive_error_event_writes"],
                },
                state=state,
            )

            print(f"✗ Device {device.hostname or device.ip} ({device_id}) - error: {str(exc)}")


async def collector_loop() -> None:
    """Main collector loop."""
    print("Starting Arista Collector")
    print(f"  Max concurrent polls: {MAX_CONCURRENT}")
    print(f"  Polling timeout: {POLLING_TIMEOUT}s")
    print(f"  Offline threshold: {OFFLINE_THRESHOLD_SEC}s")
    print(f"  Identity enforcement mode: {IDENTITY_ENFORCEMENT_MODE}")
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
