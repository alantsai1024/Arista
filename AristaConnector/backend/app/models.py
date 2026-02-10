from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    hostname = Column(String(255), nullable=True, index=True)
    ip = Column(String(45), nullable=False, index=True)
    port = Column(Integer, default=443, nullable=False)
    username = Column(String(100), nullable=False)
    password_enc = Column(Text, nullable=False)  # Encrypted password
    interval_sec = Column(Integer, default=10, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    identity = relationship(
        "DeviceIdentity",
        back_populates="device",
        uselist=False,
        cascade="all, delete-orphan",
    )
    events = relationship("Event", back_populates="device", cascade="all, delete-orphan")


class DeviceIdentity(Base):
    __tablename__ = "device_identities"

    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    mode = Column(String(16), nullable=False, default="auto")
    expected_fingerprint = Column(String(64), nullable=True, unique=True, index=True)
    last_observed_fingerprint = Column(String(64), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="unbound", index=True)
    serial_number = Column(String(255), nullable=True)
    system_mac = Column(String(64), nullable=True)
    source = Column(String(64), nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    last_conflict_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    device = relationship("Device", back_populates="identity")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_device_created_at", "device_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=True)
    metadata_json = Column("metadata", Text, nullable=True)  # JSON stored as text
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    device = relationship("Device", back_populates="events")
