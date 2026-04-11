"""MQTT client wrapper for WiCAN device communication."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import paho.mqtt.client as mqtt

from wican_blade_mcp.models import (
    Config,
    ConnectionError,
    DeviceOfflineError,
    WicanError,
    resolve_config,
)
from wican_blade_mcp.obd import STANDARD_PIDS, decode_dtc

logger = logging.getLogger(__name__)

# Topic patterns (device_id substituted at runtime)
TOPIC_OBD_RESPONSE = "wican/{device_id}/obd/response"
TOPIC_OBD_REQUEST = "wican/{device_id}/obd/request"
TOPIC_CAN_RX = "wican/{device_id}/can/rx"
TOPIC_CAN_TX = "wican/{device_id}/can/tx"
TOPIC_STATUS = "wican/{device_id}/status"

# Timeouts
RESPONSE_TIMEOUT = 10.0
CONNECT_TIMEOUT = 5.0


class WicanClient:
    """MQTT-based client for communicating with a WiCAN Pro device."""

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or resolve_config()
        self._mqtt: mqtt.Client | None = None
        self._connected = False
        self._device_id: str | None = self._config.wican.device_id
        self._pending_responses: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._last_state: dict[str, Any] = {}
        self._last_status: dict[str, Any] = {}
        self._can_buffer: list[dict[str, Any]] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def _topics(self, pattern: str) -> str:
        """Resolve a topic pattern with the device ID."""
        device_id = self._device_id or "+"
        return pattern.format(device_id=device_id)

    def connect(self) -> None:
        """Connect to the MQTT broker."""
        if self._connected and self._mqtt is not None:
            return

        self._loop = asyncio.get_event_loop()
        self._mqtt = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self._config.mqtt.client_id,
        )

        if self._config.mqtt.username:
            self._mqtt.username_pw_set(
                self._config.mqtt.username,
                self._config.mqtt.password,
            )

        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_message = self._on_message
        self._mqtt.on_disconnect = self._on_disconnect

        try:
            self._mqtt.connect(
                self._config.mqtt.broker,
                self._config.mqtt.port,
                keepalive=60,
            )
            self._mqtt.loop_start()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MQTT broker: {e}") from e

        # Wait for connection
        deadline = time.monotonic() + CONNECT_TIMEOUT
        while not self._connected and time.monotonic() < deadline:
            time.sleep(0.1)

        if not self._connected:
            raise ConnectionError(
                f"Timed out connecting to MQTT broker at {self._config.mqtt.broker}:{self._config.mqtt.port}"
            )

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._mqtt is not None:
            self._mqtt.loop_stop()
            self._mqtt.disconnect()
            self._connected = False
            self._mqtt = None

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, rc: Any, properties: Any = None) -> None:
        """Handle MQTT connection."""
        if isinstance(rc, int):
            reason_code = rc
        else:
            reason_code = rc.value if hasattr(rc, "value") else int(rc)

        if reason_code == 0:
            self._connected = True
            # Subscribe to all WiCAN topics
            client.subscribe(self._topics(TOPIC_OBD_RESPONSE))
            client.subscribe(self._topics(TOPIC_CAN_RX))
            client.subscribe(self._topics(TOPIC_STATUS))
            logger.info("Connected to MQTT broker, subscribed to WiCAN topics")
        else:
            logger.error("MQTT connection failed with code %s", reason_code)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, *args: Any) -> None:
        """Handle MQTT disconnection."""
        self._connected = False
        logger.warning("Disconnected from MQTT broker")

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Handle incoming MQTT messages."""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Failed to decode message on %s", msg.topic)
            return

        # Auto-discover device ID from topic
        if self._device_id is None:
            parts = msg.topic.split("/")
            if len(parts) >= 2 and parts[0] == "wican":
                self._device_id = parts[1]
                logger.info("Auto-discovered WiCAN device: %s", self._device_id)

        # Route message
        if "/obd/response" in msg.topic:
            self._handle_obd_response(payload)
        elif "/can/rx" in msg.topic:
            self._handle_can_rx(payload)
        elif "/status" in msg.topic:
            self._last_status = payload

    def _handle_obd_response(self, payload: dict[str, Any]) -> None:
        """Process an OBD-II response."""
        pid_key = payload.get("pid", payload.get("name", ""))
        self._last_state[pid_key] = {
            "value": payload.get("value"),
            "unit": payload.get("unit", ""),
            "raw": payload.get("raw", ""),
            "timestamp": time.time(),
        }

        # Resolve any pending futures
        if pid_key in self._pending_responses and self._loop is not None:
            future = self._pending_responses.pop(pid_key)
            self._loop.call_soon_threadsafe(future.set_result, payload)

    def _handle_can_rx(self, payload: dict[str, Any]) -> None:
        """Buffer incoming CAN frames."""
        self._can_buffer.append({
            "id": payload.get("id", payload.get("frame_id", "")),
            "data": payload.get("data", payload.get("bytes", "")),
            "timestamp": time.time(),
        })
        # Keep buffer bounded
        if len(self._can_buffer) > 1000:
            self._can_buffer = self._can_buffer[-500:]

    def _ensure_connected(self) -> None:
        """Ensure we have an active MQTT connection."""
        if not self._connected:
            self.connect()

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a message to the MQTT broker."""
        self._ensure_connected()
        if self._mqtt is None:
            raise ConnectionError("Not connected to MQTT broker")
        self._mqtt.publish(
            self._topics(topic),
            json.dumps(payload),
            qos=1,
        )

    def request_pid(self, pid_name: str) -> None:
        """Request a standard OBD-II PID from the WiCAN device."""
        pid_def = STANDARD_PIDS.get(pid_name)
        if pid_def is None:
            raise WicanError(f"Unknown PID: {pid_name}")

        self._publish(TOPIC_OBD_REQUEST, {
            "mode": f"{pid_def.mode:02X}",
            "pid": f"{pid_def.pid:02X}",
            "name": pid_name,
        })

    def request_dtcs(self) -> None:
        """Request diagnostic trouble codes (Mode 03)."""
        self._publish(TOPIC_OBD_REQUEST, {"mode": "03"})

    def clear_dtcs(self) -> None:
        """Clear diagnostic trouble codes (Mode 04). Requires write gate."""
        self._publish(TOPIC_OBD_REQUEST, {"mode": "04"})

    def send_can_frame(self, frame_id: str, data: str) -> None:
        """Send a raw CAN frame. Requires write gate."""
        self._publish(TOPIC_CAN_TX, {"id": frame_id, "data": data})

    def get_cached_state(self) -> dict[str, Any]:
        """Return the latest cached OBD-II state."""
        return dict(self._last_state)

    def get_status(self) -> dict[str, Any]:
        """Return the latest device status."""
        return dict(self._last_status)

    def get_can_buffer(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent CAN frames from the buffer."""
        return list(self._can_buffer[-limit:])

    def get_vin(self) -> str | None:
        """Request and return the VIN (Mode 09, PID 02)."""
        self._publish(TOPIC_OBD_REQUEST, {"mode": "09", "pid": "02", "name": "VIN"})
        return self._last_state.get("VIN", {}).get("value")

    def is_online(self) -> bool:
        """Check if the WiCAN device appears to be online."""
        if not self._connected:
            return False
        status = self._last_status
        if not status:
            return False
        last_seen = status.get("timestamp", 0)
        return (time.time() - last_seen) < 60

    @property
    def device_id(self) -> str | None:
        """Return the resolved device ID."""
        return self._device_id


# Module-level singleton
_client: WicanClient | None = None


def get_client() -> WicanClient:
    """Get or create the singleton WiCAN client."""
    global _client
    if _client is None:
        _client = WicanClient()
        _client.connect()
    return _client
