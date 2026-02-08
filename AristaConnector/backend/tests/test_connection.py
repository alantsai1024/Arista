"""
Tests for device connection testing endpoint.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_test_connection_endpoint(client: AsyncClient, db_session):
    """Test the test-connection endpoint"""
    # Create a device first
    device_data = {
        "ip": "192.168.1.1",
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10
    }
    
    create_response = await client.post("/devices", json=device_data)
    device_id = create_response.json()["id"]
    
    # Mock the eAPI client
    with patch('app.routers.devices.test_connection', new_callable=AsyncMock) as mock_test:
        mock_test.return_value = (True, "Connection successful", "test-hostname")
        
        response = await client.post(f"/devices/{device_id}/test-connection")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "Connection successful" in data["message"]
        assert data["hostname"] == "test-hostname"


@pytest.mark.asyncio
async def test_test_connection_failure(client: AsyncClient, db_session):
    """Test connection failure scenario"""
    device_data = {
        "ip": "192.168.1.1",
        "username": "admin",
        "password": "admin123",
        "interval_sec": 10
    }
    
    create_response = await client.post("/devices", json=device_data)
    device_id = create_response.json()["id"]
    
    # Mock connection failure
    with patch('app.routers.devices.test_connection', new_callable=AsyncMock) as mock_test:
        mock_test.return_value = (False, "Connection timeout", None)
        
        response = await client.post(f"/devices/{device_id}/test-connection")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert "timeout" in data["message"].lower()


@pytest.mark.asyncio
async def test_test_connection_device_not_found(client: AsyncClient):
    """Test connection test for non-existent device"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(f"/devices/{fake_id}/test-connection")
    assert response.status_code == 404
