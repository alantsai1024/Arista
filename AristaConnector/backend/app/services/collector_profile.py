"""
Collector profile shared by polling, MQTT mapping, and raw-topic compatibility.
"""
from __future__ import annotations

from typing import Any


_COLLECTOR_PROFILE = [
    {
        "name": "system-clock",
        "cmds": ["show clock"],
        "format": "json",
        "topic": "network/arista/raw/show-clock",
    },
    {
        "name": "system-hostname",
        "cmds": ["show hostname"],
        "format": "json",
        "topic": "network/arista/raw/show-hostname",
    },
    {
        "name": "interfaces-status",
        "cmds": ["show interfaces status"],
        "format": "json",
        "topic": "network/arista/raw/show-interfaces-status",
    },
    {
        "name": "system-version",
        "cmds": ["show version"],
        "format": "json",
        "topic": "network/arista/raw/show-version",
    },
]


def get_collectors() -> list[dict[str, Any]]:
    """Return a copy of collector profile."""
    return [
        {
            "name": collector["name"],
            "cmds": list(collector["cmds"]),
            "format": collector["format"],
            "topic": collector["topic"],
        }
        for collector in _COLLECTOR_PROFILE
    ]


def get_poll_commands() -> list[str]:
    """Return all eAPI commands to run in one runCmds call."""
    commands: list[str] = []
    for collector in _COLLECTOR_PROFILE:
        commands.extend(collector["cmds"])
    return commands


def _fallback_collector_name(command: str) -> str:
    return command.replace(" ", "-").lower()


def get_collector_by_command(command: str) -> dict[str, Any] | None:
    """Return collector config by command string."""
    for collector in _COLLECTOR_PROFILE:
        if command in collector["cmds"]:
            return collector
    return None


def get_collector_name_for_command(command: str) -> str:
    collector = get_collector_by_command(command)
    if collector:
        return str(collector["name"])
    return _fallback_collector_name(command)


def get_raw_topic_for_command(command: str) -> str:
    collector = get_collector_by_command(command)
    if collector:
        return str(collector["topic"])
    return f"network/arista/raw/{_fallback_collector_name(command)}"
