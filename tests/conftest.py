"""Shared test fixtures."""

from __future__ import annotations

import pytest

from wican_blade_mcp.models import Config, MqttConfig, WicanConfig


@pytest.fixture
def config() -> Config:
    """Test configuration with defaults."""
    return Config(
        mqtt=MqttConfig(broker="localhost", port=1883),
        wican=WicanConfig(write_enabled=False),
    )


@pytest.fixture
def write_config() -> Config:
    """Test configuration with writes enabled."""
    return Config(
        mqtt=MqttConfig(broker="localhost", port=1883),
        wican=WicanConfig(write_enabled=True),
    )
