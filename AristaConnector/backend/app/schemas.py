from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from app.utils.validation import validate_ip_address, validate_interval


class DeviceBase(BaseModel):
    hostname: Optional[str] = Field(None, max_length=255)
    ip: str = Field(..., max_length=45)
    port: int = Field(default=443, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)  # Will be encrypted before storage
    interval_sec: int = Field(default=10, ge=5, le=300)
    enabled: bool = Field(default=True)

    @field_validator('ip')
    @classmethod
    def validate_ip(cls, v: str) -> str:
        if not validate_ip_address(v):
            raise ValueError('Invalid IP address format')
        return v

    @field_validator('interval_sec')
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if not validate_interval(v):
            raise ValueError('Interval must be between 5 and 300 seconds')
        return v


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    hostname: Optional[str] = Field(None, max_length=255)
    ip: Optional[str] = Field(None, max_length=45)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=1)
    interval_sec: Optional[int] = Field(None, ge=5, le=300)
    enabled: Optional[bool] = None

    @field_validator('ip')
    @classmethod
    def validate_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not validate_ip_address(v):
            raise ValueError('Invalid IP address format')
        return v

    @field_validator('interval_sec')
    @classmethod
    def validate_interval(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not validate_interval(v):
            raise ValueError('Interval must be between 5 and 300 seconds')
        return v


class DeviceResponse(BaseModel):
    id: UUID
    hostname: Optional[str]
    ip: str
    port: int
    username: str
    interval_sec: int
    enabled: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DeviceStatus(BaseModel):
    device_id: UUID
    status: str
    last_seen: Optional[datetime]
    online: bool
    recent_stats: Optional[Dict[str, Any]] = None


class EventResponse(BaseModel):
    id: UUID
    device_id: UUID
    event_type: str
    message: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceLatency(BaseModel):
    device_id: UUID
    hostname: Optional[str]
    ip: str
    latency_ms: Optional[float]


class FleetHealth(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    degraded_devices: int
    devices: list[DeviceStatus]
    top_latency_devices: list[DeviceLatency] = []


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    hostname: Optional[str] = None
