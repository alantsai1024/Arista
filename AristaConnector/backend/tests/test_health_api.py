"""
Tests for /health/fleet response completeness and status counting behavior.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.models import Event


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    def set_raw(self, key: str, value: str | bytes) -> None:
        self.store[key] = value if isinstance(value, bytes) else value.encode()

    async def mget(self, *keys):
        if len(keys) == 1 and isinstance(keys[0], list):
            keys = tuple(keys[0])
        return [self.store.get(key) for key in keys]


@pytest.mark.asyncio
async def test_fleet_health_includes_recent_stats_for_each_device(client: AsyncClient, db_session, monkeypatch):
    redis_client = FakeRedis()

    async def fake_get_redis_client():
        return redis_client

    monkeypatch.setattr("app.routers.health.get_redis_client", fake_get_redis_client)

    payload1 = {
        "hostname": "veos-01",
        "ip": "192.168.56.2",
        "username": "admin",
        "password": "pw1",
        "interval_sec": 10,
    }
    payload2 = {
        "hostname": "veos-02",
        "ip": "192.168.56.3",
        "username": "admin",
        "password": "pw2",
        "interval_sec": 10,
    }

    create1 = await client.post("/devices", json=payload1)
    create2 = await client.post("/devices", json=payload2)
    assert create1.status_code == 201
    assert create2.status_code == 201

    device1_id = UUID(create1.json()["id"])
    device2_id = UUID(create2.json()["id"])

    now = datetime.now()
    db_session.add_all(
        [
            Event(
                device_id=device1_id,
                event_type="poll_success",
                message="ok",
                created_at=now - timedelta(minutes=20),
            ),
            Event(
                device_id=device1_id,
                event_type="poll_error",
                message="timeout",
                created_at=now - timedelta(minutes=5),
            ),
            Event(
                device_id=device2_id,
                event_type="poll_success",
                message="old event",
                created_at=now - timedelta(hours=2),
            ),
        ]
    )
    await db_session.commit()

    redis_client.set_raw(f"device:{device1_id}:status", "online")
    redis_client.set_raw(f"device:{device1_id}:last_seen", now.isoformat())
    redis_client.set_raw(f"device:{device1_id}:latency_ms", "12.5")

    redis_client.set_raw(f"device:{device2_id}:status", "degraded")
    redis_client.set_raw(f"device:{device2_id}:last_seen", (now - timedelta(seconds=40)).isoformat())
    redis_client.set_raw(f"device:{device2_id}:latency_ms", "23.9")

    response = await client.get("/health/fleet")
    assert response.status_code == 200
    data = response.json()

    assert data["online_devices"] == 1
    assert data["degraded_devices"] == 1
    assert data["offline_devices"] == 0

    by_id = {item["device_id"]: item for item in data["devices"]}
    stats1 = by_id[str(device1_id)]["recent_stats"]
    stats2 = by_id[str(device2_id)]["recent_stats"]

    assert stats1["total_events_last_hour"] == 2
    assert stats1["events_by_type"]["poll_success"] == 1
    assert stats1["events_by_type"]["poll_error"] == 1
    assert stats1["last_event_at"] is not None
    assert stats1["latency_ms"] == 12.5

    assert stats2["total_events_last_hour"] == 0
    assert stats2["events_by_type"] == {}
    assert stats2["last_event_at"] is None
    assert stats2["latency_ms"] == 23.9


@pytest.mark.asyncio
async def test_fleet_health_unknown_status_counted_as_offline(client: AsyncClient, monkeypatch):
    redis_client = FakeRedis()

    async def fake_get_redis_client():
        return redis_client

    monkeypatch.setattr("app.routers.health.get_redis_client", fake_get_redis_client)

    payload = {
        "hostname": "veos-unknown",
        "ip": "192.168.56.10",
        "username": "admin",
        "password": "pw",
        "interval_sec": 10,
    }
    create = await client.post("/devices", json=payload)
    assert create.status_code == 201

    device_id = create.json()["id"]
    redis_client.set_raw(f"device:{device_id}:status", "unknown")

    response = await client.get("/health/fleet")
    assert response.status_code == 200
    data = response.json()

    assert data["online_devices"] == 0
    assert data["degraded_devices"] == 0
    assert data["offline_devices"] == 1

    device_status = data["devices"][0]
    assert device_status["status"] == "unknown"
    assert device_status["recent_stats"]["total_events_last_hour"] == 0


@pytest.mark.asyncio
async def test_fleet_health_ip_conflict_not_counted_online(client: AsyncClient, monkeypatch):
    redis_client = FakeRedis()

    async def fake_get_redis_client():
        return redis_client

    monkeypatch.setattr("app.routers.health.get_redis_client", fake_get_redis_client)

    create = await client.post(
        "/devices",
        json={
            "hostname": "veos-conflict",
            "ip": "192.168.56.20",
            "username": "admin",
            "password": "pw",
            "interval_sec": 10,
        },
    )
    assert create.status_code == 201
    device_id = create.json()["id"]

    now = datetime.now()
    redis_client.set_raw(f"device:{device_id}:status", "ip_conflict")
    redis_client.set_raw(f"device:{device_id}:last_seen", now.isoformat())

    response = await client.get("/health/fleet")
    assert response.status_code == 200
    payload = response.json()

    assert payload["online_devices"] == 0
    assert payload["degraded_devices"] == 0
    assert payload["offline_devices"] == 1
    assert payload["devices"][0]["status"] == "ip_conflict"
    assert payload["devices"][0]["online"] is False
