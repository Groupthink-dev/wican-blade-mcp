"""Configuration, environment resolution, and write gates."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class MqttConfig:
    """MQTT broker connection settings."""

    broker: str = "localhost"
    port: int = 1883
    username: str | None = None
    password: str | None = None
    client_id: str = "wican-blade-mcp"


@dataclass
class WicanConfig:
    """WiCAN device and feature settings."""

    device_id: str | None = None
    dbc_path: str | None = None
    write_enabled: bool = False
    poll_pids: list[str] = field(default_factory=lambda: [
        "SPEED", "RPM", "COOLANT_TEMP", "FUEL_LEVEL",
        "ENGINE_LOAD", "THROTTLE_POS", "BATTERY_VOLTAGE",
    ])


@dataclass
class Config:
    """Combined configuration from environment."""

    mqtt: MqttConfig
    wican: WicanConfig


def resolve_config() -> Config:
    """Resolve configuration from environment variables."""
    mqtt = MqttConfig(
        broker=os.environ.get("MQTT_BROKER", "localhost"),
        port=int(os.environ.get("MQTT_PORT", "1883")),
        username=os.environ.get("MQTT_USERNAME"),
        password=os.environ.get("MQTT_PASSWORD"),
        client_id=os.environ.get("MQTT_CLIENT_ID", "wican-blade-mcp"),
    )
    wican = WicanConfig(
        device_id=os.environ.get("WICAN_DEVICE_ID"),
        dbc_path=os.environ.get("WICAN_DBC_PATH"),
        write_enabled=os.environ.get("WICAN_WRITE_ENABLED", "").lower() == "true",
    )
    return Config(mqtt=mqtt, wican=wican)


class WicanError(Exception):
    """Base error for WiCAN operations."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.details = details


class ConnectionError(WicanError):
    """MQTT connection failed."""


class DeviceOfflineError(WicanError):
    """WiCAN device is not responding."""


class DecodingError(WicanError):
    """CAN frame decoding failed."""


def check_write_gate() -> str | None:
    """Return error message if writes are disabled, else None."""
    if not os.environ.get("WICAN_WRITE_ENABLED", "").lower() == "true":
        return "Error: Write operations are disabled. Set WICAN_WRITE_ENABLED=true to enable."
    return None


def check_confirm_gate(confirm: bool, action: str) -> str | None:
    """Return error message if confirm is not set, else None."""
    if not confirm:
        return f"Error: {action} requires explicit confirmation. Set confirm=true to proceed."
    return None
