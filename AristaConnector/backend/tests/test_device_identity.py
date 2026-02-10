"""
Unit tests for device identity fingerprint extraction.
"""
from __future__ import annotations

import pytest

from app.services.device_identity import (
    compute_identity_fingerprint,
    extract_identity_observation,
    normalize_identity_fingerprint,
    normalize_serial_number,
    normalize_system_mac,
)


def test_normalize_serial_and_mac():
    assert normalize_serial_number(" sn-001 ") == "SN-001"
    assert normalize_system_mac("00:11:22:33:44:55") == "001122334455"
    assert normalize_system_mac("0011.2233.4455") == "001122334455"


def test_compute_identity_fingerprint_is_deterministic():
    fp1 = compute_identity_fingerprint("SN-001", "00:11:22:33:44:55")
    fp2 = compute_identity_fingerprint(" sn-001 ", "0011.2233.4455")
    assert fp1 == fp2
    assert fp1 is not None
    assert len(fp1) == 64


def test_extract_identity_observation_from_poll_payload():
    observation = extract_identity_observation(
        {
            "show version": {
                "serialNumber": "SN-ABC",
                "systemMacAddress": "00:aa:bb:cc:dd:ee",
            }
        }
    )
    assert observation.serial_number == "SN-ABC"
    assert observation.system_mac == "00aabbccddee"
    assert observation.fingerprint is not None
    assert observation.is_insufficient is False


def test_extract_identity_observation_handles_missing_identity():
    observation = extract_identity_observation({"show version": {"version": "4.31.1F"}})
    assert observation.serial_number is None
    assert observation.system_mac is None
    assert observation.fingerprint is None
    assert observation.is_insufficient is True


def test_normalize_identity_fingerprint_validation():
    valid = "A" * 64
    assert normalize_identity_fingerprint(valid) == valid.lower()

    with pytest.raises(ValueError):
        normalize_identity_fingerprint("abc")
