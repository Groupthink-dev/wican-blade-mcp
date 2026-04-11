"""OBD-II PID definitions and response decoding."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PidDefinition:
    """Standard OBD-II PID definition."""

    pid: int
    name: str
    description: str
    unit: str
    mode: int = 0x01
    bytes_returned: int = 2

    def decode(self, data: bytes) -> float | int:
        """Decode raw OBD-II response bytes to a value."""
        return DECODERS.get(self.name, _decode_raw)(data)


def _decode_raw(data: bytes) -> int:
    return int.from_bytes(data, "big")


def _decode_rpm(data: bytes) -> float:
    return ((data[0] * 256) + data[1]) / 4.0


def _decode_speed(data: bytes) -> int:
    return data[0]


def _decode_temp(data: bytes) -> int:
    return data[0] - 40


def _decode_fuel_level(data: bytes) -> float:
    return data[0] * 100.0 / 255.0


def _decode_load(data: bytes) -> float:
    return data[0] * 100.0 / 255.0


def _decode_throttle(data: bytes) -> float:
    return data[0] * 100.0 / 255.0


def _decode_voltage(data: bytes) -> float:
    return ((data[0] * 256) + data[1]) / 1000.0


DECODERS: dict[str, type[object] | object] = {
    "RPM": _decode_rpm,
    "SPEED": _decode_speed,
    "COOLANT_TEMP": _decode_temp,
    "INTAKE_TEMP": _decode_temp,
    "FUEL_LEVEL": _decode_fuel_level,
    "ENGINE_LOAD": _decode_load,
    "THROTTLE_POS": _decode_throttle,
    "BATTERY_VOLTAGE": _decode_voltage,
}

# Standard OBD-II Mode 01 PIDs
STANDARD_PIDS: dict[str, PidDefinition] = {
    "RPM": PidDefinition(pid=0x0C, name="RPM", description="Engine RPM", unit="rpm"),
    "SPEED": PidDefinition(pid=0x0D, name="SPEED", description="Vehicle speed", unit="km/h", bytes_returned=1),
    "COOLANT_TEMP": PidDefinition(
        pid=0x05, name="COOLANT_TEMP", description="Engine coolant temperature", unit="°C", bytes_returned=1
    ),
    "INTAKE_TEMP": PidDefinition(
        pid=0x0F, name="INTAKE_TEMP", description="Intake air temperature", unit="°C", bytes_returned=1
    ),
    "FUEL_LEVEL": PidDefinition(
        pid=0x2F, name="FUEL_LEVEL", description="Fuel tank level", unit="%", bytes_returned=1
    ),
    "ENGINE_LOAD": PidDefinition(
        pid=0x04, name="ENGINE_LOAD", description="Calculated engine load", unit="%", bytes_returned=1
    ),
    "THROTTLE_POS": PidDefinition(
        pid=0x11, name="THROTTLE_POS", description="Throttle position", unit="%", bytes_returned=1
    ),
    "BATTERY_VOLTAGE": PidDefinition(
        pid=0x42, name="BATTERY_VOLTAGE", description="Control module voltage", unit="V"
    ),
    "FUEL_PRESSURE": PidDefinition(
        pid=0x0A, name="FUEL_PRESSURE", description="Fuel pressure", unit="kPa", bytes_returned=1
    ),
    "MAF_RATE": PidDefinition(pid=0x10, name="MAF_RATE", description="MAF air flow rate", unit="g/s"),
    "RUN_TIME": PidDefinition(pid=0x1F, name="RUN_TIME", description="Run time since engine start", unit="s"),
    "DISTANCE_MIL": PidDefinition(
        pid=0x21, name="DISTANCE_MIL", description="Distance traveled with MIL on", unit="km"
    ),
    "ODOMETER": PidDefinition(
        pid=0xA6, name="ODOMETER", description="Odometer", unit="km", bytes_returned=4
    ),
}

# OBD-II Mode 03 DTC prefixes
DTC_PREFIXES: dict[int, str] = {
    0: "P0",  # Powertrain (generic)
    1: "P1",  # Powertrain (manufacturer)
    2: "P2",  # Powertrain (generic)
    3: "P3",  # Powertrain (generic/manufacturer)
    4: "C0",  # Chassis (generic)
    5: "C1",  # Chassis (manufacturer)
    6: "C2",  # Chassis (manufacturer)
    7: "C3",  # Chassis (manufacturer)
    8: "B0",  # Body (generic)
    9: "B1",  # Body (manufacturer)
    10: "B2",  # Body (manufacturer)
    11: "B3",  # Body (manufacturer)
    12: "U0",  # Network (generic)
    13: "U1",  # Network (manufacturer)
    14: "U2",  # Network (manufacturer)
    15: "U3",  # Network (manufacturer)
}


def decode_dtc(byte_a: int, byte_b: int) -> str:
    """Decode a 2-byte DTC into a human-readable code (e.g., P0301)."""
    prefix_index = (byte_a >> 4) & 0x0F
    prefix = DTC_PREFIXES.get(prefix_index, "P0")
    digit2 = byte_a & 0x0F
    digit3 = (byte_b >> 4) & 0x0F
    digit4 = byte_b & 0x0F
    return f"{prefix}{digit2}{digit3}{digit4}"
