"""Tests for OBD-II PID decoding."""

from __future__ import annotations

from wican_blade_mcp.obd import STANDARD_PIDS, decode_dtc


class TestPidDecoding:
    def test_decode_speed(self) -> None:
        pid = STANDARD_PIDS["SPEED"]
        assert pid.decode(bytes([60])) == 60  # 60 km/h

    def test_decode_rpm(self) -> None:
        pid = STANDARD_PIDS["RPM"]
        # RPM = ((A * 256) + B) / 4
        assert pid.decode(bytes([0x0B, 0xB8])) == 750.0  # idle

    def test_decode_coolant_temp(self) -> None:
        pid = STANDARD_PIDS["COOLANT_TEMP"]
        # Temp = A - 40
        assert pid.decode(bytes([130])) == 90  # 90°C normal operating

    def test_decode_fuel_level(self) -> None:
        pid = STANDARD_PIDS["FUEL_LEVEL"]
        # Fuel = A * 100 / 255
        result = pid.decode(bytes([128]))
        assert 50.0 < result < 51.0  # ~50.2%

    def test_decode_throttle(self) -> None:
        pid = STANDARD_PIDS["THROTTLE_POS"]
        assert pid.decode(bytes([0])) == 0.0
        result = pid.decode(bytes([255]))
        assert result == 100.0

    def test_decode_engine_load(self) -> None:
        pid = STANDARD_PIDS["ENGINE_LOAD"]
        result = pid.decode(bytes([128]))
        assert 50.0 < result < 51.0


class TestDtcDecoding:
    def test_powertrain_generic(self) -> None:
        # P0301 = Cylinder 1 Misfire
        assert decode_dtc(0x03, 0x01) == "P0301"

    def test_chassis_code(self) -> None:
        # C0035
        assert decode_dtc(0x40, 0x35) == "C0035"

    def test_body_code(self) -> None:
        # B0100
        assert decode_dtc(0x81, 0x00) == "B0100"

    def test_network_code(self) -> None:
        # U0100
        assert decode_dtc(0xC1, 0x00) == "U0100"
