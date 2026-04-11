"""WiCAN Blade MCP server — universal vehicle monitoring via meatPi WiCAN Pro."""

from __future__ import annotations

import asyncio
import os
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from wican_blade_mcp.client import get_client
from wican_blade_mcp.formatters import (
    error_response,
    format_battery,
    format_can_frames,
    format_device_status,
    format_diagnostics,
    format_trip,
    format_vehicle_state,
)
from wican_blade_mcp.models import (
    WicanError,
    check_confirm_gate,
    check_write_gate,
)
from wican_blade_mcp.obd import STANDARD_PIDS

mcp = FastMCP(
    "WiCAN Vehicle",
    instructions=(
        "Universal vehicle monitoring via meatPi WiCAN Pro OBD-II adapter. "
        "Reads standard engine and drivetrain data, diagnostic trouble codes, "
        "and raw CAN bus frames over MQTT. Works with any OBD-II vehicle."
    ),
)


async def _run[T](fn: object, *args: object) -> T:
    """Run a blocking function in a thread."""
    return await asyncio.to_thread(fn, *args)  # type: ignore[arg-type]


@mcp.tool()
async def wican_vehicles() -> str:
    """List connected WiCAN devices with vehicle identity and connection status."""
    try:
        client = await _run(get_client)
        status = client.get_status()
        device_id = client.device_id
        connected = client.is_online()

        result = format_device_status(status, device_id, connected)

        # Try to get VIN if available
        state = client.get_cached_state()
        if vin := state.get("VIN", {}).get("value"):
            result += f"\nvin={vin}"

        return result
    except WicanError as e:
        return error_response(str(e), e.details)


@mcp.tool()
async def wican_state(
    refresh: Annotated[bool, Field(description="Request fresh data from the vehicle (default: use cached)")] = False,
) -> str:
    """Vehicle snapshot: speed, RPM, fuel, coolant temp, battery voltage, throttle, engine load."""
    try:
        client = await _run(get_client)

        if refresh:
            for pid_name in ["SPEED", "RPM", "COOLANT_TEMP", "FUEL_LEVEL", "ENGINE_LOAD",
                             "THROTTLE_POS", "BATTERY_VOLTAGE", "INTAKE_TEMP"]:
                if pid_name in STANDARD_PIDS:
                    client.request_pid(pid_name)
            # Brief wait for responses
            await asyncio.sleep(2.0)

        state = client.get_cached_state()
        return format_vehicle_state(state)
    except WicanError as e:
        return error_response(str(e), e.details)


@mcp.tool()
async def wican_diagnostics(
    refresh: Annotated[bool, Field(description="Request fresh DTC read from the vehicle")] = False,
) -> str:
    """Read diagnostic trouble codes, MIL status, and monitor readiness."""
    try:
        client = await _run(get_client)

        if refresh:
            client.request_dtcs()
            await asyncio.sleep(2.0)

        state = client.get_cached_state()

        dtcs: list[str] = []
        mil_on = False
        monitor_status: dict[str, object] | None = None

        if dtc_data := state.get("DTC"):
            raw = dtc_data.get("value", {})
            if isinstance(raw, dict):
                dtcs = raw.get("codes", [])
                mil_on = raw.get("mil", False)
                monitor_status = raw.get("monitors")
            elif isinstance(raw, list):
                dtcs = raw

        return format_diagnostics(dtcs, mil_on, monitor_status)
    except WicanError as e:
        return error_response(str(e), e.details)


@mcp.tool()
async def wican_battery(
    refresh: Annotated[bool, Field(description="Request fresh battery data")] = False,
) -> str:
    """Battery voltage, alternator state, and EV SoC if CAN-decoded."""
    try:
        client = await _run(get_client)

        if refresh:
            client.request_pid("BATTERY_VOLTAGE")
            client.request_pid("ENGINE_LOAD")
            await asyncio.sleep(1.5)

        state = client.get_cached_state()
        return format_battery(state)
    except WicanError as e:
        return error_response(str(e), e.details)


@mcp.tool()
async def wican_trip() -> str:
    """Current speed, RPM, run time, odometer, and fuel level."""
    try:
        client = await _run(get_client)
        state = client.get_cached_state()
        return format_trip(state)
    except WicanError as e:
        return error_response(str(e), e.details)


@mcp.tool()
async def wican_can_read(
    frame_id: Annotated[str | None, Field(description="Filter by CAN frame ID (hex, e.g. '7E8')")] = None,
    limit: Annotated[int, Field(description="Maximum frames to return", ge=1, le=200)] = 50,
) -> str:
    """Read raw CAN bus frames from the buffer. Use with DBC files for manufacturer-specific decoding."""
    try:
        client = await _run(get_client)
        frames = client.get_can_buffer(limit=limit)

        if frame_id is not None:
            target = frame_id.upper().lstrip("0X")
            frames = [f for f in frames if str(f.get("id", "")).upper().lstrip("0X") == target]

        return format_can_frames(frames)
    except WicanError as e:
        return error_response(str(e), e.details)


@mcp.tool()
async def wican_dtc_clear(
    confirm: Annotated[bool, Field(description="Must be true to execute. Clears all DTCs and resets MIL.")] = False,
) -> str:
    """Clear diagnostic trouble codes and reset the MIL warning light. Dual-gated: requires WICAN_WRITE_ENABLED=true and confirm=true."""
    gate = check_write_gate()
    if gate:
        return gate
    gate = check_confirm_gate(confirm, "Clearing DTCs")
    if gate:
        return gate

    try:
        client = await _run(get_client)
        client.clear_dtcs()
        await asyncio.sleep(1.0)
        return "DTCs cleared. MIL reset. Run wican_diagnostics with refresh=true to verify."
    except WicanError as e:
        return error_response(str(e), e.details)


@mcp.tool()
async def wican_can_send(
    frame_id: Annotated[str, Field(description="CAN frame ID in hex (e.g. '7DF')")],
    data: Annotated[str, Field(description="CAN data bytes in hex (e.g. '0201050000000000')")],
    confirm: Annotated[bool, Field(description="Must be true to execute. Sends a raw CAN frame.")] = False,
) -> str:
    """Send a raw CAN frame to the vehicle bus. Dual-gated: requires WICAN_WRITE_ENABLED=true and confirm=true."""
    gate = check_write_gate()
    if gate:
        return gate
    gate = check_confirm_gate(confirm, "Sending raw CAN frame")
    if gate:
        return gate

    try:
        client = await _run(get_client)
        client.send_can_frame(frame_id, data)
        return f"CAN frame sent: id=0x{frame_id} data={data}"
    except WicanError as e:
        return error_response(str(e), e.details)


# --- Transport ---

HTTP_HOST = os.environ.get("WICAN_MCP_HOST", "127.0.0.1")
HTTP_PORT = int(os.environ.get("WICAN_MCP_PORT", "8100"))
TRANSPORT = os.environ.get("TRANSPORT", "stdio")


def main() -> None:
    """Run the MCP server."""
    if TRANSPORT == "http":
        mcp.run(transport="streamable-http", host=HTTP_HOST, port=HTTP_PORT)
    else:
        mcp.run(transport="stdio")
