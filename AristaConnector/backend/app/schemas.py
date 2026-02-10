from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional, Dict, Any, Literal
from uuid import UUID
from app.services.device_identity import normalize_identity_fingerprint
from app.utils.validation import validate_ip_address, validate_interval


class DeviceBase(BaseModel):
    hostname: Optional[str] = Field(None, max_length=255)
    ip: str = Field(..., max_length=45)
    port: int = Field(default=443, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)  # Will be encrypted before storage
    interval_sec: int = Field(default=10, ge=5, le=300)
    enabled: bool = Field(default=True)
    identity_mode: Literal["auto", "manual"] = Field(default="auto")
    expected_identity_fingerprint: Optional[str] = Field(default=None, min_length=64, max_length=64)

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

    @field_validator('expected_identity_fingerprint')
    @classmethod
    def validate_expected_identity_fingerprint(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return normalize_identity_fingerprint(v)

    @model_validator(mode='after')
    def validate_identity_mode_requirements(self):
        if self.identity_mode == "manual" and not self.expected_identity_fingerprint:
            raise ValueError('expected_identity_fingerprint is required when identity_mode=manual')
        return self


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
    identity_mode: Optional[Literal["auto", "manual"]] = None
    expected_identity_fingerprint: Optional[str] = Field(default=None, min_length=64, max_length=64)

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

    @field_validator('expected_identity_fingerprint')
    @classmethod
    def validate_expected_identity_fingerprint(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return normalize_identity_fingerprint(v)


class DeviceResponse(BaseModel):
    id: UUID
    hostname: Optional[str]
    ip: str
    port: int
    username: str
    interval_sec: int
    enabled: bool
    identity_mode: str
    identity_status: Optional[str] = None
    expected_identity_fingerprint: Optional[str] = None
    last_observed_identity_fingerprint: Optional[str] = None
    identity_last_verified_at: Optional[datetime] = None
    identity_last_conflict_at: Optional[datetime] = None
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
