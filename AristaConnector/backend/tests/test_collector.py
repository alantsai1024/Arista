"""
Small-scale collector tests (1-3 devices, no 30-device mock load test).
"""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.dao.events import get_recent_events
from app.models import Device, DeviceIdentity, Event
from app.services.retention_sink import RetentionSink
from app.utils.encryption import encrypt_password


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    async def setex(self, key: str, ttl: int, value: str) -> None:  # noqa: ARG002
        self.store[key] = str(value).encode()

    async def set(self, key: str, value: str) -> None:
        self.store[key] = str(value).encode()

    async def get(self, key: str) -> bytes | None:
        return self.store.get(key)


def build_runtime_context(db_session, tmp_path):
    redis_client = FakeRedis()
    semaphore = asyncio.Semaphore(10)
    sink = RetentionSink(base_dir=str(tmp_path / "runtime"), enabled=True, targets={"*"})
    event_session_factory = async_sessionmaker(
        db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return redis_client, semaphore, sink, event_session_factory


async def create_test_device(
    db_session,
    *,
    hostname: str,
    ip: str,
) -> Device:
    device = Device(
        hostname=hostname,
        ip=ip,
        port=443,
        username="admin",
        password_enc=encrypt_password("0000"),
        interval_sec=10,
        enabled=True,
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


async def count_device_events(db_session, device_id, event_type: str) -> int:
    query = (
        select(func.count())
        .select_from(Event)
        .where(Event.device_id == device_id, Event.event_type == event_type)
    )
    result = await db_session.execute(query)
    return int(result.scalar_one() or 0)


@pytest.mark.asyncio
async def test_collector_mock_small_scale(monkeypatch, db_session, tmp_path):
    """
    Poll 3 mocked devices once and verify events + Redis status.
    """
    from collector import device_states, poll_single_device

    device_states.clear()

    devices: list[Device] = []
    for idx in range(3):
        device = Device(
            hostname=f"veos-{idx + 1}",
            ip=f"192.168.56.{idx + 2}",
            port=443,
            username="admin",
            password_enc=encrypt_password("0000"),
            interval_sec=10,
            enabled=True,
        )
        db_session.add(device)
        devices.append(device)
    await db_session.commit()
    for device in devices:
        await db_session.refresh(device)

    async def fake_poll_device(**kwargs):  # noqa: ANN003, ANN202
        ip = kwargs["ip"]
        suffix = ip.split(".")[-1]
        return (
            True,
            None,
            {
                "show clock": {"clockSource": {"local": True}},
                "show hostname": {"hostname": "veos-mock"},
                "show interfaces status": {"interfaceStatuses": {}},
                "show version": {
                    "version": "4.31.1F",
                    "serialNumber": f"SN-MOCK-{suffix}",
                    "systemMacAddress": f"00:11:22:33:44:{int(suffix):02x}",
                },
            },
            12.34,
        )

    monkeypatch.setattr("collector.poll_device", fake_poll_device)
    monkeypatch.setattr("collector.publish_state", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_telemetry", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_raw_compat", lambda **kwargs: None)

    redis_client = FakeRedis()
    semaphore = asyncio.Semaphore(10)
    sink = RetentionSink(base_dir=str(tmp_path / "runtime"), enabled=True, targets={"*"})
    event_session_factory = async_sessionmaker(
        db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    for device in devices:
        await poll_single_device(device, semaphore, redis_client, sink, event_session_factory)

    for device in devices:
        status_key = f"device:{device.id}:status"
        status = await redis_client.get(status_key)
        assert status is not None
        assert status.decode() == "online"

        events = await get_recent_events(db_session, device.id, limit=5)
        assert len(events) >= 1
        assert events[0].event_type == "poll_success"


@pytest.mark.asyncio
async def test_collector_concurrent_event_writes(monkeypatch, db_session, tmp_path):
    """
    Poll multiple devices concurrently and verify event writes do not conflict.
    """
    from collector import device_states, poll_single_device

    device_states.clear()

    devices: list[Device] = []
    for idx in range(3):
        device = Device(
            hostname=f"veos-concurrent-{idx + 1}",
            ip=f"10.0.0.{idx + 1}",
            port=443,
            username="admin",
            password_enc=encrypt_password("0000"),
            interval_sec=10,
            enabled=True,
        )
        db_session.add(device)
        devices.append(device)
    await db_session.commit()
    for device in devices:
        await db_session.refresh(device)

    async def fake_poll_device(**kwargs):  # noqa: ANN003, ANN202
        ip = kwargs["ip"]
        suffix = ip.split(".")[-1]
        return (
            True,
            None,
            {
                "show clock": {"clockSource": {"local": True}},
                "show hostname": {"hostname": "veos-mock"},
                "show interfaces status": {"interfaceStatuses": {}},
                "show version": {
                    "version": "4.31.1F",
                    "serialNumber": f"SN-MOCK-{suffix}",
                    "systemMacAddress": f"00:11:22:33:55:{int(suffix):02x}",
                },
            },
            10.0,
        )

    monkeypatch.setattr("collector.poll_device", fake_poll_device)
    monkeypatch.setattr("collector.publish_state", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_telemetry", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_raw_compat", lambda **kwargs: None)

    redis_client = FakeRedis()
    semaphore = asyncio.Semaphore(10)
    sink = RetentionSink(base_dir=str(tmp_path / "runtime"), enabled=True, targets={"*"})
    event_session_factory = async_sessionmaker(
        db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    tasks = [
        poll_single_device(device, semaphore, redis_client, sink, event_session_factory)
        for device in devices
    ]
    await asyncio.gather(*tasks)

    for device in devices:
        status_key = f"device:{device.id}:status"
        status = await redis_client.get(status_key)
        assert status is not None
        assert status.decode() == "online"

        events = await get_recent_events(db_session, device.id, limit=5)
        assert events
        assert events[0].event_type == "poll_success"


@pytest.mark.asyncio
async def test_poll_error_event_writes_capped_at_four(monkeypatch, db_session, tmp_path):
    from collector import device_states, poll_single_device

    device_states.clear()
    device = await create_test_device(db_session, hostname="veos-fail-cap", ip="10.10.10.1")

    async def fake_poll_device(**kwargs):  # noqa: ANN003, ANN202, ARG001
        return False, "Connection timeout", None, None

    monkeypatch.setattr("collector.poll_device", fake_poll_device)
    monkeypatch.setattr("collector.calculate_backoff_delay", lambda *args, **kwargs: 0)
    monkeypatch.setattr("collector.publish_state", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_telemetry", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_raw_compat", lambda **kwargs: None)

    redis_client, semaphore, sink, event_session_factory = build_runtime_context(db_session, tmp_path)

    for _ in range(6):
        await poll_single_device(device, semaphore, redis_client, sink, event_session_factory)

    poll_error_count = await count_device_events(db_session, device.id, "poll_error")
    assert poll_error_count == 4

    state = device_states[device.id]
    assert state["consecutive_error_event_writes"] == 4
    assert state["error_event_suppressed"] is True


@pytest.mark.asyncio
async def test_poll_error_cap_resets_after_success(monkeypatch, db_session, tmp_path):
    from collector import device_states, poll_single_device

    device_states.clear()
    device = await create_test_device(db_session, hostname="veos-recover", ip="10.10.10.2")

    outcomes = [
        (False, "Connection timeout", None, None),
        (False, "Connection timeout", None, None),
        (False, "Connection timeout", None, None),
        (False, "Connection timeout", None, None),
        (False, "Connection timeout", None, None),
        (
            True,
            None,
            {
                "show clock": {"clockSource": {"local": True}},
                "show hostname": {"hostname": "veos-recovered"},
                "show interfaces status": {"interfaceStatuses": {}},
                "show version": {
                    "version": "4.31.1F",
                    "serialNumber": "SN-MOCK-3",
                    "systemMacAddress": "00:11:22:33:44:77",
                },
            },
            9.5,
        ),
        (False, "Connection timeout", None, None),
    ]

    async def fake_poll_device(**kwargs):  # noqa: ANN003, ANN202, ARG001
        return outcomes.pop(0)

    monkeypatch.setattr("collector.poll_device", fake_poll_device)
    monkeypatch.setattr("collector.calculate_backoff_delay", lambda *args, **kwargs: 0)
    monkeypatch.setattr("collector.publish_state", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_telemetry", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_raw_compat", lambda **kwargs: None)

    redis_client, semaphore, sink, event_session_factory = build_runtime_context(db_session, tmp_path)

    for _ in range(7):
        await poll_single_device(device, semaphore, redis_client, sink, event_session_factory)

    poll_error_count = await count_device_events(db_session, device.id, "poll_error")
    poll_success_count = await count_device_events(db_session, device.id, "poll_success")
    assert poll_error_count == 5
    assert poll_success_count == 1

    state = device_states[device.id]
    assert state["consecutive_error_event_writes"] == 1
    assert state["error_event_suppressed"] is False


@pytest.mark.asyncio
async def test_poll_error_cap_isolated_per_device_under_concurrency(monkeypatch, db_session, tmp_path):
    from collector import device_states, poll_single_device

    device_states.clear()
    devices = [
        await create_test_device(db_session, hostname=f"veos-par-{idx}", ip=f"10.10.20.{idx}")
        for idx in range(1, 4)
    ]

    async def fake_poll_device(**kwargs):  # noqa: ANN003, ANN202, ARG001
        return False, "Connection timeout", None, None

    monkeypatch.setattr("collector.poll_device", fake_poll_device)
    monkeypatch.setattr("collector.calculate_backoff_delay", lambda *args, **kwargs: 0)
    monkeypatch.setattr("collector.publish_state", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_telemetry", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_raw_compat", lambda **kwargs: None)

    redis_client, semaphore, sink, event_session_factory = build_runtime_context(db_session, tmp_path)

    for _ in range(5):
        tasks = [
            poll_single_device(device, semaphore, redis_client, sink, event_session_factory)
            for device in devices
        ]
        await asyncio.gather(*tasks)

    for device in devices:
        poll_error_count = await count_device_events(db_session, device.id, "poll_error")
        assert poll_error_count == 4
        state = device_states[device.id]
        assert state["consecutive_error_event_writes"] == 4
        assert state["error_event_suppressed"] is True


@pytest.mark.asyncio
async def test_poll_error_cap_applies_to_exception_path(monkeypatch, db_session, tmp_path):
    from collector import device_states, poll_single_device

    device_states.clear()
    device = await create_test_device(db_session, hostname="veos-exc-cap", ip="10.10.30.1")

    async def fake_poll_device(**kwargs):  # noqa: ANN003, ANN202, ARG001
        raise RuntimeError("boom")

    monkeypatch.setattr("collector.poll_device", fake_poll_device)
    monkeypatch.setattr("collector.calculate_backoff_delay", lambda *args, **kwargs: 0)
    monkeypatch.setattr("collector.publish_state", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_telemetry", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_raw_compat", lambda **kwargs: None)

    redis_client, semaphore, sink, event_session_factory = build_runtime_context(db_session, tmp_path)

    for _ in range(6):
        await poll_single_device(device, semaphore, redis_client, sink, event_session_factory)

    poll_error_count = await count_device_events(db_session, device.id, "poll_error")
    assert poll_error_count == 4

    state = device_states[device.id]
    assert state["consecutive_error_event_writes"] == 4
    assert state["error_event_suppressed"] is True


@pytest.mark.asyncio
async def test_collector_auto_binds_identity_on_first_success(monkeypatch, db_session, tmp_path):
    from collector import device_states, poll_single_device

    device_states.clear()
    device = await create_test_device(db_session, hostname="veos-bind", ip="10.20.30.1")

    async def fake_poll_device(**kwargs):  # noqa: ANN003, ANN202, ARG001
        return (
            True,
            None,
            {
                "show clock": {"clockSource": {"local": True}},
                "show hostname": {"hostname": "veos-bind"},
                "show interfaces status": {"interfaceStatuses": {}},
                "show version": {
                    "version": "4.31.1F",
                    "serialNumber": "SN-BIND-1",
                    "systemMacAddress": "00:11:22:AA:BB:CC",
                },
            },
            11.2,
        )

    monkeypatch.setattr("collector.poll_device", fake_poll_device)
    monkeypatch.setattr("collector.publish_state", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_telemetry", lambda **kwargs: None)
    monkeypatch.setattr("collector.publish_raw_compat", lambda **kwargs: None)

    redis_client, semaphore, sink, event_session_factory = build_runtime_context(db_session, tmp_path)
    await poll_single_device(device, semaphore, redis_client, sink, event_session_factory)

    status = await redis_client.get(f"device:{device.id}:status")
    assert status is not None
    assert status.decode() == "online"

    identity_query = select(DeviceIdentity).where(DeviceIdentity.device_id == device.id)
    identity = (await db_session.execute(identity_query)).scalar_one_or_none()
    assert identity is not None
    assert identity.expected_fingerprint is not None
    assert identity.status == "verified"

    bound_count = await count_device_events(db_session, device.id, "identity_bound")
    assert bound_count == 1


@pytest.mark.asyncio
async def test_collector_ip_conflict_blocks_telemetry_publish(monkeypatch, db_session, tmp_path):
    from collector import device_states, poll_single_device

    device_states.clear()
    device = await create_test_device(db_session, hostname="veos-conflict", ip="10.20.30.2")

    outcomes = [
        (
            True,
            None,
            {
                "show clock": {"clockSource": {"local": True}},
                "show hostname": {"hostname": "veos-conflict"},
                "show interfaces status": {"interfaceStatuses": {}},
                "show version": {
                    "version": "4.31.1F",
                    "serialNumber": "SN-CF-1",
                    "systemMacAddress": "00:11:22:AA:CC:01",
                },
            },
            10.0,
        ),
        (
            True,
            None,
            {
                "show clock": {"clockSource": {"local": True}},
                "show hostname": {"hostname": "veos-conflict"},
                "show interfaces status": {"interfaceStatuses": {}},
                "show version": {
                    "version": "4.31.1F",
                    "serialNumber": "SN-CF-2",
                    "systemMacAddress": "00:11:22:AA:CC:02",
                },
            },
            10.5,
        ),
    ]

    telemetry_calls: list[dict] = []
    raw_calls: list[dict] = []
    state_calls: list[dict] = []

    async def fake_poll_device(**kwargs):  # noqa: ANN003, ANN202, ARG001
        return outcomes.pop(0)

    monkeypatch.setattr("collector.poll_device", fake_poll_device)
    monkeypatch.setattr("collector.publish_state", lambda **kwargs: state_calls.append(kwargs))
    monkeypatch.setattr("collector.publish_telemetry", lambda **kwargs: telemetry_calls.append(kwargs))
    monkeypatch.setattr("collector.publish_raw_compat", lambda **kwargs: raw_calls.append(kwargs))

    redis_client, semaphore, sink, event_session_factory = build_runtime_context(db_session, tmp_path)
    await poll_single_device(device, semaphore, redis_client, sink, event_session_factory)
    telemetry_after_first_poll = len(telemetry_calls)
    raw_after_first_poll = len(raw_calls)

    await poll_single_device(device, semaphore, redis_client, sink, event_session_factory)

    status = await redis_client.get(f"device:{device.id}:status")
    assert status is not None
    assert status.decode() == "ip_conflict"

    # Second poll hit identity conflict, telemetry/raw must not continue publishing.
    assert len(telemetry_calls) == telemetry_after_first_poll
    assert len(raw_calls) == raw_after_first_poll
    assert state_calls[-1]["data"]["status"] == "ip_conflict"

    conflict_count = await count_device_events(db_session, device.id, "identity_conflict")
    assert conflict_count >= 1
