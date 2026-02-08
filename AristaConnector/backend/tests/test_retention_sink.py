"""
Tests for retention sink behavior.
"""
from __future__ import annotations

from app.services.retention_sink import RetentionSink


def test_retention_sink_non_blocking(tmp_path):
    sink = RetentionSink(base_dir=str(tmp_path / "runtime"), enabled=True, targets={"*"})

    class NonSerializable:
        pass

    payload = {
        "device": "veos-test",
        "collector": "system-clock",
        "cmds": ["show clock"],
        "format": "json",
        "raw": {"bad": NonSerializable()},
        "ts": 1234567890,
    }

    result = sink.persist(topic="network/arista/raw/show-clock", payload=payload)
    assert result["ok"] is False
    assert "error" in result

    # log_event must never raise even if values are unusual
    sink.log_event({"collector": "system-clock", "error": object(), "ts": 1234567891})
