"""Tests for output formatters."""

from __future__ import annotations

import time

from wican_blade_mcp.formatters import (
    error_response,
    format_battery,
    format_can_frames,
    format_device_status,
    format_diagnostics,
    format_trip,
    format_vehicle_state,
)


class TestFormatVehicleState:
    def test_empty_state(self) -> None:
        result = format_vehicle_state({})
        assert "No vehicle data" in result

    def test_with_data(self) -> None:
        state = {
            "SPEED": {"value": 60, "unit": "km/h"},
            "RPM": {"value": 2500, "unit": "rpm"},
        }
        result = format_vehicle_state(state)
        assert "SPEED | 60 km/h" in result
        assert "RPM | 2500 rpm" in result


class TestFormatDeviceStatus:
    def test_basic_status(self) -> None:
        result = format_device_status({}, "wican_abc", True)
        assert "device_id=wican_abc" in result
        assert "mqtt=connected" in result

    def test_disconnected(self) -> None:
        result = format_device_status({}, None, False)
        assert "device_id=unknown" in result
        assert "mqtt=disconnected" in result

    def test_with_firmware(self) -> None:
        status = {"firmware": "3.45", "ssid": "HomeWiFi", "rssi": -65}
        result = format_device_status(status, "dev1", True)
        assert "firmware=3.45" in result
        assert "wifi=HomeWiFi" in result
        assert "rssi=-65dBm" in result


class TestFormatDiagnostics:
    def test_no_dtcs(self) -> None:
        result = format_diagnostics([], False)
        assert "MIL | OFF" in result
        assert "DTCs | 0 active" in result

    def test_with_dtcs(self) -> None:
        result = format_diagnostics(["P0301", "P0420"], True)
        assert "MIL | ON" in result
        assert "DTCs | 2 active" in result
        assert "P0301" in result
        assert "P0420" in result


class TestFormatBattery:
    def test_empty(self) -> None:
        result = format_battery({})
        assert "No battery data" in result

    def test_with_voltage(self) -> None:
        state = {"BATTERY_VOLTAGE": {"value": 14.2}}
        result = format_battery(state)
        assert "voltage=14.2 V" in result


class TestFormatCanFrames:
    def test_empty(self) -> None:
        result = format_can_frames([])
        assert "No CAN frames" in result

    def test_with_frames(self) -> None:
        frames = [
            {"id": "7E8", "data": "0341050000000000", "timestamp": time.time()},
            {"id": "7E9", "data": "0341060000000000", "timestamp": time.time()},
        ]
        result = format_can_frames(frames)
        assert "0x7E8" in result
        assert "0x7E9" in result


class TestFormatTrip:
    def test_empty(self) -> None:
        result = format_trip({})
        assert "No trip data" in result

    def test_with_data(self) -> None:
        state = {
            "SPEED": {"value": 80},
            "RPM": {"value": 3000},
            "FUEL_LEVEL": {"value": 65.0},
        }
        result = format_trip(state)
        assert "speed=80 km/h" in result
        assert "rpm=3000" in result
        assert "fuel=65.0%" in result


class TestErrorResponse:
    def test_simple(self) -> None:
        assert error_response("Something broke") == "Error: Something broke"

    def test_with_details(self) -> None:
        result = error_response("Connection failed", "Broker at 192.168.1.1 unreachable")
        assert "Error: Connection failed" in result
        assert "Details: Broker at 192.168.1.1 unreachable" in result
