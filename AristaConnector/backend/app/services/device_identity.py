"""
Device identity helpers for fingerprint extraction and validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Any, Mapping, Optional

IDENTITY_MODE_AUTO = "auto"
IDENTITY_MODE_MANUAL = "manual"

IDENTITY_STATUS_UNBOUND = "unbound"
IDENTITY_STATUS_VERIFIED = "verified"
IDENTITY_STATUS_CONFLICT = "conflict"
IDENTITY_STATUS_INSUFFICIENT = "insufficient_identity"

IDENTITY_SOURCE_SHOW_VERSION = "show version"

_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")
_HEX_CHARS_RE = re.compile(r"[^0-9a-fA-F]")


@dataclass(frozen=True)
class IdentityObservation:
    serial_number: Optional[str]
    system_mac: Optional[str]
    fingerprint: Optional[str]
    source: str = IDENTITY_SOURCE_SHOW_VERSION

    @property
    def is_insufficient(self) -> bool:
        return self.fingerprint is None


def normalize_identity_fingerprint(value: Optional[str]) -> Optional[str]:
    """
    Normalize fingerprint to lowercase hex string.
    """
    if value is None:
        return None

    normalized = value.strip().lower()
    if not normalized:
        return None

    if not _FINGERPRINT_RE.fullmatch(normalized):
        raise ValueError("identity fingerprint must be 64-char sha256 hex")

    return normalized


def normalize_serial_number(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def normalize_system_mac(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    condensed = _HEX_CHARS_RE.sub("", value)
    if not condensed:
        return None

    return condensed.lower()


def compute_identity_fingerprint(
    serial_number: Optional[str],
    system_mac: Optional[str],
) -> Optional[str]:
    """
    Compute deterministic fingerprint from serial + system MAC.
    """
    serial = normalize_serial_number(serial_number)
    mac = normalize_system_mac(system_mac)

    if not serial and not mac:
        return None

    payload = f"serial={serial or ''}|mac={mac or ''}"
    return sha256(payload.encode("utf-8")).hexdigest()


def _get_casefold_value(
    payload: Mapping[str, Any],
    candidate_keys: list[str],
) -> Optional[str]:
    """
    Return first non-empty value from payload by case-insensitive keys.
    """
    lookup = {str(key).lower(): value for key, value in payload.items()}
    for key in candidate_keys:
        value = lookup.get(key.lower())
        if isinstance(value, str) and value.strip():
            return value
    return None


def extract_identity_observation(
    poll_data: Optional[dict[str, Any]],
) -> IdentityObservation:
    """
    Build identity observation from collector poll results.
    """
    show_version: Mapping[str, Any] = {}
    if poll_data and isinstance(poll_data.get(IDENTITY_SOURCE_SHOW_VERSION), Mapping):
        show_version = poll_data[IDENTITY_SOURCE_SHOW_VERSION]

    serial = _get_casefold_value(
        show_version,
        [
            "serialNumber",
            "serial_number",
            "serial",
        ],
    )
    system_mac = _get_casefold_value(
        show_version,
        [
            "systemMacAddress",
            "system_mac_address",
            "systemMac",
            "macAddress",
            "mac",
        ],
    )

    normalized_serial = normalize_serial_number(serial)
    normalized_mac = normalize_system_mac(system_mac)
    fingerprint = compute_identity_fingerprint(normalized_serial, normalized_mac)

    return IdentityObservation(
        serial_number=normalized_serial,
        system_mac=normalized_mac,
        fingerprint=fingerprint,
        source=IDENTITY_SOURCE_SHOW_VERSION,
    )
