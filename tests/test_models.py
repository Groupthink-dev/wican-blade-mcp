"""Tests for configuration and write gates."""

from __future__ import annotations

import os
from unittest.mock import patch

from wican_blade_mcp.models import (
    check_confirm_gate,
    check_write_gate,
    resolve_config,
)


class TestResolveConfig:
    def test_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = resolve_config()
            assert config.mqtt.broker == "localhost"
            assert config.mqtt.port == 1883
            assert config.mqtt.username is None
            assert config.mqtt.password is None
            assert config.wican.device_id is None
            assert config.wican.dbc_path is None
            assert config.wican.write_enabled is False

    def test_from_env(self) -> None:
        env = {
            "MQTT_BROKER": "192.168.1.100",
            "MQTT_PORT": "8883",
            "MQTT_USERNAME": "user",
            "MQTT_PASSWORD": "pass",
            "WICAN_DEVICE_ID": "wican_abc123",
            "WICAN_DBC_PATH": "/tmp/honda.dbc",
            "WICAN_WRITE_ENABLED": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_config()
            assert config.mqtt.broker == "192.168.1.100"
            assert config.mqtt.port == 8883
            assert config.mqtt.username == "user"
            assert config.mqtt.password == "pass"
            assert config.wican.device_id == "wican_abc123"
            assert config.wican.dbc_path == "/tmp/honda.dbc"
            assert config.wican.write_enabled is True

    def test_write_enabled_case_insensitive(self) -> None:
        with patch.dict(os.environ, {"WICAN_WRITE_ENABLED": "True"}, clear=True):
            config = resolve_config()
            assert config.wican.write_enabled is True


class TestWriteGates:
    def test_write_gate_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = check_write_gate()
            assert result is not None
            assert "WICAN_WRITE_ENABLED" in result

    def test_write_gate_enabled(self) -> None:
        with patch.dict(os.environ, {"WICAN_WRITE_ENABLED": "true"}, clear=True):
            result = check_write_gate()
            assert result is None

    def test_confirm_gate_false(self) -> None:
        result = check_confirm_gate(False, "Clearing DTCs")
        assert result is not None
        assert "confirm=true" in result

    def test_confirm_gate_true(self) -> None:
        result = check_confirm_gate(True, "Clearing DTCs")
        assert result is None
