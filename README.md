# Prusa Buddy Metrics

A Home Assistant custom integration that receives real-time metrics from Prusa Buddy-based printers (e.g. Core One) over UDP syslog and exposes them as sensors and binary sensors.

## How it works

The integration listens on a configurable UDP port for syslog messages sent by the printer. Each message contains one or more lines in **InfluxDB line protocol** format. Metrics are automatically classified into numeric sensors (temperature, voltage, fan RPM, etc.) or binary sensors (state flags) based on keyword rules.

Sensors are created dynamically on first receipt — no manual configuration of individual metrics is needed.

## Requirements

- Home Assistant (with custom component support)
- A Prusa Buddy-based printer (e.g. Core One) configured to send syslog/metrics over UDP

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant.
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**.
3. Add `https://github.com/walderbash/prusa-buddy-metrics` as an **Integration**.
4. Search for **Prusa Buddy Metrics** and install it.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/prusa_buddy_metrics/` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Prusa Buddy Metrics**.
3. Set the **UDP port** to listen on (default: `8514`).
4. Click **Submit**.

You can update the port later via the integration's **Configure** option.

## Printer setup

On the printer touchscreen:

1. Open **Settings**
2. Navigate to **Network**
3. Scroll down to **Metrics & Log**
4. Set **Host** to the IP address of your Home Assistant machine
5. Set **Port** to `8514`
6. Open **Metrics List** and enable the metrics you want to receive

> For more detail on the UDP metrics format, see the [Prusa Firmware Buddy documentation](https://github.com/prusa3d/Prusa-Firmware-Buddy/blob/master/doc/metrics.md).


## Useful metrics

Below are some metrics worth enabling on the printer. Enable them via **Settings → Network → Metrics & Log → Metrics List**.

Entity IDs are based on the printer's MAC address (e.g. `aa_bb_cc_dd_ee_ff`).

| Metric | Entity ID (example) | Type | Description |
|--------|---------------------|------|-------------|
| `chamber_temp` | `sensor.prusa_buddy_aa_bb_cc_dd_ee_ff_chamber_temp` | Sensor | Chamber temperature in °C |
| `xbe_fan` | `sensor.prusa_buddy_aa_bb_cc_dd_ee_ff_xbe_fan_1` | Sensor | Chamber fan speed in RPM — one entity per fan (e.g. `_1`, `_2`) |
| `door_sensor` | `binary_sensor.prusa_buddy_aa_bb_cc_dd_ee_ff_door_sensor` | Binary sensor | Door open/closed state |

## Sensors

Sensors are auto-discovered from incoming data. Classification is based on the measurement and field name:

| Keyword(s) in name | Type | Device class | Unit |
|--------------------|------|--------------|------|
| `temp` | Sensor | temperature | °C |
| `voltage` | Sensor | voltage | V |
| `current` | Sensor | current | A |
| `xbe_fan` | Sensor | — | rpm |
| `pwm` | Sensor | power_factor | % |
| `heap`, `free`, `total` | Sensor | — | B |
| `recv`, `sent`, `bytes` | Sensor (total_increasing) | — | B |
| `usage` | Sensor | — | % |
| `state`, `enabled`, `stall` | Binary sensor | — | — |

Sensors become **unavailable** automatically if no data is received for 5 minutes.

## Multiple printers

Multiple printers can send to the same UDP port simultaneously. Each printer is identified by its MAC address (extracted from the syslog envelope) and will appear as a separate device in Home Assistant. No additional configuration is needed.

## License

MIT
