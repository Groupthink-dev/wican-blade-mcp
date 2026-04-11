"""Output formatting for MCP tool responses."""

from __future__ import annotations

from typing import Any


def format_vehicle_state(state: dict[str, Any]) -> str:
    """Format cached OBD-II state as compact pipe-delimited lines."""
    if not state:
        return "No vehicle data available. The WiCAN device may be offline or the engine may be off."

    lines: list[str] = []
    for name, entry in sorted(state.items()):
        value = entry.get("value")
        unit = entry.get("unit", "")
        if value is not None:
            lines.append(f"{name} | {value} {unit}".strip())

    return "\n".join(lines) if lines else "No data received yet."


def format_device_status(status: dict[str, Any], device_id: str | None, connected: bool) -> str:
    """Format device connection and health status."""
    parts: list[str] = []
    parts.append(f"device_id={device_id or 'unknown'}")
    parts.append(f"mqtt={'connected' if connected else 'disconnected'}")

    if fw := status.get("firmware"):
        parts.append(f"firmware={fw}")
    if proto := status.get("protocol"):
        parts.append(f"protocol={proto}")
    if ssid := status.get("ssid"):
        parts.append(f"wifi={ssid}")
    if rssi := status.get("rssi"):
        parts.append(f"rssi={rssi}dBm")

    return " | ".join(parts)


def format_diagnostics(dtcs: list[str], mil_on: bool, monitor_status: dict[str, Any] | None = None) -> str:
    """Format diagnostic trouble codes and MIL status."""
    lines: list[str] = []
    lines.append(f"MIL | {'ON' if mil_on else 'OFF'}")
    lines.append(f"DTCs | {len(dtcs)} active")

    if dtcs:
        lines.append("")
        for code in dtcs:
            lines.append(f"  {code}")

    if monitor_status:
        lines.append("")
        lines.append("## Monitor Readiness")
        for monitor, ready in sorted(monitor_status.items()):
            lines.append(f"  {monitor} | {'ready' if ready else 'not ready'}")

    return "\n".join(lines)


def format_battery(state: dict[str, Any]) -> str:
    """Format battery and charging-related state."""
    parts: list[str] = []

    if voltage := state.get("BATTERY_VOLTAGE"):
        parts.append(f"voltage={voltage.get('value')} V")
    if load := state.get("ENGINE_LOAD"):
        parts.append(f"engine_load={load.get('value')}%")

    # EV fields from CAN decoding (if available)
    if soc := state.get("EV_SOC"):
        parts.append(f"soc={soc.get('value')}%")
    if charging := state.get("EV_CHARGING"):
        parts.append(f"charging={'yes' if charging.get('value') else 'no'}")

    if not parts:
        return "No battery data available."

    return " | ".join(parts)


def format_can_frames(frames: list[dict[str, Any]]) -> str:
    """Format raw CAN frames as compact lines."""
    if not frames:
        return "No CAN frames in buffer."

    lines: list[str] = []
    for frame in frames:
        frame_id = frame.get("id", "???")
        data = frame.get("data", "")
        lines.append(f"0x{frame_id} | {data}")

    return "\n".join(lines)


def format_trip(state: dict[str, Any]) -> str:
    """Format trip-related data."""
    parts: list[str] = []

    if speed := state.get("SPEED"):
        parts.append(f"speed={speed.get('value')} km/h")
    if rpm := state.get("RPM"):
        parts.append(f"rpm={rpm.get('value')}")
    if run_time := state.get("RUN_TIME"):
        parts.append(f"run_time={run_time.get('value')}s")
    if odo := state.get("ODOMETER"):
        parts.append(f"odometer={odo.get('value')} km")
    if fuel := state.get("FUEL_LEVEL"):
        parts.append(f"fuel={fuel.get('value')}%")

    if not parts:
        return "No trip data available. Engine may be off."

    return " | ".join(parts)


def error_response(message: str, details: str = "") -> str:
    """Format a consistent error response."""
    if details:
        return f"Error: {message}\nDetails: {details}"
    return f"Error: {message}"
