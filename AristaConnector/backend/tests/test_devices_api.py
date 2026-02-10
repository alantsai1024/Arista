"""
Tests for device management API endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_device(client: AsyncClient, db_session):
    """Test creating a new device"""
    device_data = {
        "hostname": "test-device",
        "ip": "192.168.1.1",
        "port": 443,
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10,
        "enabled": True
    }
    
    response = await client.post("/devices", json=device_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["hostname"] == "test-device"
    assert data["ip"] == "192.168.1.1"
    assert data["port"] == 443
    assert data["username"] == "admin"
    assert data["interval_sec"] == 10
    assert data["enabled"] is True
    assert data["identity_mode"] == "auto"
    assert data["identity_status"] == "unbound"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_device_invalid_ip(client: AsyncClient):
    """Test creating device with invalid IP"""
    device_data = {
        "ip": "invalid-ip",
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10
    }
    
    response = await client.post("/devices", json=device_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_device_invalid_interval(client: AsyncClient):
    """Test creating device with invalid interval"""
    device_data = {
        "ip": "192.168.1.1",
        "username": "admin",
        "password": "admin123",
        "interval_sec": 3  # Too low
    }
    
    response = await client.post("/devices", json=device_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_device_duplicate_ip(client: AsyncClient, db_session):
    """Test creating device with duplicate IP"""
    device_data = {
        "ip": "192.168.1.1",
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10
    }
    
    # Create first device
    response1 = await client.post("/devices", json=device_data)
    assert response1.status_code == 201
    
    # Try to create duplicate
    response2 = await client.post("/devices", json=device_data)
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_devices(client: AsyncClient, db_session):
    """Test listing all devices"""
    # Create test devices
    device1_data = {
        "ip": "192.168.1.1",
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10
    }
    device2_data = {
        "ip": "192.168.1.2",
        "username": "admin",
        "password": "admin123",
        "interval_sec": 20
    }
    
    await client.post("/devices", json=device1_data)
    await client.post("/devices", json=device2_data)
    
    response = await client.get("/devices")
    assert response.status_code == 200
    
    devices = response.json()
    assert len(devices) == 2
    assert devices[0]["ip"] in ["192.168.1.1", "192.168.1.2"]
    assert devices[1]["ip"] in ["192.168.1.1", "192.168.1.2"]


@pytest.mark.asyncio
async def test_get_device(client: AsyncClient, db_session):
    """Test getting a specific device"""
    device_data = {
        "hostname": "test-device",
        "ip": "192.168.1.1",
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10
    }
    
    create_response = await client.post("/devices", json=device_data)
    assert create_response.status_code == 201
    device_id = create_response.json()["id"]
    
    response = await client.get(f"/devices/{device_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == device_id
    assert data["hostname"] == "test-device"
    assert data["ip"] == "192.168.1.1"


@pytest.mark.asyncio
async def test_get_device_not_found(client: AsyncClient):
    """Test getting non-existent device"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/devices/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_device(client: AsyncClient, db_session):
    """Test updating a device"""
    device_data = {
        "ip": "192.168.1.1",
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10,
        "enabled": True
    }
    
    create_response = await client.post("/devices", json=device_data)
    device_id = create_response.json()["id"]
    
    # Update interval and enabled
    update_data = {
        "interval_sec": 30,
        "enabled": False
    }
    
    response = await client.patch(f"/devices/{device_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["interval_sec"] == 30
    assert data["enabled"] is False


@pytest.mark.asyncio
async def test_update_device_credentials(client: AsyncClient, db_session):
    """Test updating device credentials"""
    device_data = {
        "ip": "192.168.1.1",
        "username": "admin",
        "password": "oldpassword",
        "interval_sec": 10
    }
    
    create_response = await client.post("/devices", json=device_data)
    device_id = create_response.json()["id"]
    
    # Update username and password
    update_data = {
        "username": "newadmin",
        "password": "newpassword"
    }
    
    response = await client.patch(f"/devices/{device_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["username"] == "newadmin"


@pytest.mark.asyncio
async def test_update_device_invalid_interval(client: AsyncClient, db_session):
    """Test updating device with invalid interval"""
    device_data = {
        "ip": "192.168.1.1",
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10
    }
    
    create_response = await client.post("/devices", json=device_data)
    device_id = create_response.json()["id"]
    
    # Try to update with invalid interval
    update_data = {"interval_sec": 400}  # Too high
    
    response = await client.patch(f"/devices/{device_id}", json=update_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_disable_device(client: AsyncClient, db_session):
    """Test disabling a device"""
    device_data = {
        "ip": "192.168.1.1",
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10,
        "enabled": True
    }
    
    create_response = await client.post("/devices", json=device_data)
    device_id = create_response.json()["id"]
    
    # Disable device
    update_data = {"enabled": False}
    response = await client.patch(f"/devices/{device_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["enabled"] is False
    
    # Verify device is disabled in database
    get_response = await client.get(f"/devices/{device_id}")
    assert get_response.json()["enabled"] is False


@pytest.mark.asyncio
async def test_update_device_not_found(client: AsyncClient):
    """Test updating non-existent device"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    update_data = {"interval_sec": 20}
    
    response = await client.patch(f"/devices/{fake_id}", json=update_data)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_device_success(client: AsyncClient, db_session):
    """Test deleting an existing device."""
    device_data = {
        "hostname": "delete-me",
        "ip": "192.168.1.200",
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10,
        "enabled": True,
    }

    create_response = await client.post("/devices", json=device_data)
    assert create_response.status_code == 201
    device_id = create_response.json()["id"]

    delete_response = await client.delete(f"/devices/{device_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/devices/{device_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_device_not_found(client: AsyncClient):
    """Test deleting a non-existent device."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.delete(f"/devices/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_device_manual_identity_requires_expected_fingerprint(client: AsyncClient):
    payload = {
        "hostname": "manual-identity-device",
        "ip": "192.168.1.210",
        "port": 443,
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10,
        "enabled": True,
        "identity_mode": "manual",
    }

    response = await client.post("/devices", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_device_duplicate_expected_identity_fingerprint_returns_409(client: AsyncClient):
    fingerprint = "f" * 64
    first = {
        "hostname": "identity-a",
        "ip": "192.168.1.211",
        "port": 443,
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10,
        "enabled": True,
        "identity_mode": "manual",
        "expected_identity_fingerprint": fingerprint,
    }
    second = {
        "hostname": "identity-b",
        "ip": "192.168.1.212",
        "port": 443,
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10,
        "enabled": True,
        "identity_mode": "manual",
        "expected_identity_fingerprint": fingerprint,
    }

    response1 = await client.post("/devices", json=first)
    assert response1.status_code == 201

    response2 = await client.post("/devices", json=second)
    assert response2.status_code == 409


@pytest.mark.asyncio
async def test_update_device_identity_mode_manual_requires_expected(client: AsyncClient):
    create_response = await client.post(
        "/devices",
        json={
            "hostname": "identity-update",
            "ip": "192.168.1.213",
            "port": 443,
            "username": "admin",
            "password": "admin123",
            "interval_sec": 10,
            "enabled": True,
        },
    )
    assert create_response.status_code == 201
    device_id = create_response.json()["id"]

    response = await client.patch(
        f"/devices/{device_id}",
        json={"identity_mode": "manual"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_device_with_manual_expected_identity(client: AsyncClient):
    create_response = await client.post(
        "/devices",
        json={
            "hostname": "identity-update-ok",
            "ip": "192.168.1.214",
            "port": 443,
            "username": "admin",
            "password": "admin123",
            "interval_sec": 10,
            "enabled": True,
        },
    )
    assert create_response.status_code == 201
    device_id = create_response.json()["id"]
    fingerprint = "a" * 64

    response = await client.patch(
        f"/devices/{device_id}",
        json={
            "identity_mode": "manual",
            "expected_identity_fingerprint": fingerprint,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["identity_mode"] == "manual"
    assert data["expected_identity_fingerprint"] == fingerprint
