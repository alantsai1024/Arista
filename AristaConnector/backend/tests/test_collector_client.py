"""
Tests for collector client profile wiring.
"""

from app.services.collector_client import get_poll_commands


def test_poll_device_includes_show_version():
    commands = get_poll_commands()
    assert "show clock" in commands
    assert "show hostname" in commands
    assert "show interfaces status" in commands
    assert "show version" in commands
