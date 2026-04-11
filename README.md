# wican-blade-mcp

Universal vehicle monitoring via [meatPi WiCAN Pro](https://www.meatpi.com/products/wican-pro) OBD-II adapter. Standard PIDs over MQTT, raw CAN bus decoding, diagnostic trouble codes, and trip data. Works with any OBD-II vehicle.

## Install

```bash
uv tool install wican-blade-mcp
```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `MQTT_BROKER` | Yes | MQTT broker hostname or IP |
| `MQTT_PORT` | No | Broker port (default: 1883) |
| `MQTT_USERNAME` | No | Broker username |
| `MQTT_PASSWORD` | No | Broker password |
| `WICAN_DEVICE_ID` | No | Device ID (auto-discovered if omitted) |
| `WICAN_DBC_PATH` | No | Path to opendbc DBC file for CAN decoding |
| `WICAN_WRITE_ENABLED` | No | Enable DTC clearing and raw CAN send |

## Tools

| Tool | Type | Description |
|------|------|-------------|
| `wican_vehicles` | read | Device connection status and vehicle identity |
| `wican_state` | read | Speed, RPM, fuel, coolant, battery, throttle, load |
| `wican_diagnostics` | read | DTCs, MIL status, monitor readiness |
| `wican_battery` | read | Battery voltage, EV SoC (if CAN-decoded) |
| `wican_trip` | read | Speed, RPM, run time, odometer, fuel level |
| `wican_can_read` | read | Raw CAN frames from buffer |
| `wican_dtc_clear` | gated | Clear DTCs and reset MIL |
| `wican_can_send` | gated | Send raw CAN frame |

## License

MIT
