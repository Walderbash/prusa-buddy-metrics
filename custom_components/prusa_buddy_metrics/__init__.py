"""Prusa Buddy Metrics - UDP to Home Assistant integration."""
from __future__ import annotations

import asyncio
import logging
import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    CONF_UDP_PORT,
    SENSOR_RULES,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]

# Syslog envelope pattern
SYSLOG_RE = re.compile(
    r"^<\d+>1\s+\S+\s+(?P<mac>\S+)\s+buddy\s+\S+\s+\S+\s+\S+\s+"
    r"(?:msg=\d+,tm=\d+,v=\d+)\s+(?P<payload>.+)$",
    re.DOTALL,
)

# InfluxDB line protocol pattern
LINE_RE = re.compile(
    r"^(?P<measurement>[^\s,]+)"
    r"(?:,(?P<tags>[^\s]+))?"
    r"\s+(?P<fields>[^\s]+)"
    r"(?:\s+[-]?\d+)?$"
)

SIGNAL_NEW_METRIC = f"{DOMAIN}_new_metric"
SIGNAL_UPDATE_METRIC = f"{DOMAIN}_update_metric"


def classify_sensor(measurement: str, field: str):
    """Return (device_class, unit, is_binary, state_class) for a measurement+field."""
    combined = f"{measurement}_{field}".lower()
    for keywords, device_class, unit, is_binary, state_class in SENSOR_RULES:
        if any(kw in combined for kw in keywords):
            return device_class, unit, is_binary, state_class
    return None, None, False, "measurement"


def parse_fields(raw: str) -> dict:
    result = {}
    for pair in raw.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            v = v.rstrip("i")
            try:
                v = int(v)
            except ValueError:
                try:
                    v = float(v)
                except ValueError:
                    pass
            result[k] = v
    return result


def parse_tags(raw: str) -> dict:
    if not raw:
        return {}
    return dict(p.split("=", 1) for p in raw.split(",") if "=" in p)


def sanitize_id(value: str) -> str:
    """Replace any character that isn't alphanumeric or underscore with '_'."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", value)


def make_unique_id(entry_id: str, printer_id: str, measurement: str, field: str, tags: dict) -> str:
    tag_suffix = "_".join(f"{k}_{v}" for k, v in sorted(tags.items()))
    parts = [entry_id, sanitize_id(printer_id), sanitize_id(measurement), sanitize_id(field)]
    if tag_suffix:
        parts.append(sanitize_id(tag_suffix))
    return "_".join(parts)


def make_entity_name(measurement: str, tags: dict) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_ ]", "", measurement.replace("_", " "))
    tag_suffix = " ".join(re.sub(r"[^a-zA-Z0-9_ ]", "", v) for v in tags.values())
    name = clean.title()
    if tag_suffix:
        name += f" {tag_suffix}"
    return name.strip()


class PrusaBuddyUDPProtocol(asyncio.DatagramProtocol):
    """Asyncio UDP protocol that parses incoming printer metrics."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        port = self.entry.options.get(CONF_UDP_PORT, self.entry.data[CONF_UDP_PORT])
        _LOGGER.info("UDP listener started on port %s", port)

    def datagram_received(self, data: bytes, addr):
        try:
            message = data.decode("utf-8", errors="replace").strip()
        except Exception:
            return

        syslog_match = SYSLOG_RE.match(message)
        printer_id = syslog_match.group("mac") if syslog_match else addr[0]
        payload = syslog_match.group("payload") if syslog_match else message

        for line in payload.splitlines():
            line = line.strip()
            if not line:
                continue
            m = LINE_RE.match(line)
            if not m:
                continue

            measurement = m.group("measurement")
            tags = parse_tags(m.group("tags"))
            fields = parse_fields(m.group("fields"))

            if not fields:
                continue

            # Pick the primary field: prefer "rpm" > "v" > "value" > first field
            primary_field = next(
                (f for f in ("rpm", "v", "value") if f in fields),
                next(iter(fields))
            )
            primary_value = fields[primary_field]
            extra_attrs = {k: v for k, v in fields.items() if k != primary_field}

            _, _, is_binary, _ = classify_sensor(measurement, primary_field)
            unique_id = make_unique_id(
                self.entry.entry_id, printer_id, measurement, primary_field, tags
            )
            name = make_entity_name(measurement, tags)

            async_dispatcher_send(
                self.hass,
                SIGNAL_NEW_METRIC,
                {
                    "unique_id": unique_id,
                    "name": name,
                    "measurement": measurement,
                    "field": primary_field,
                    "tags": tags,
                    "is_binary": is_binary,
                    "value": primary_value,
                    "extra_attrs": extra_attrs,
                    "entry_id": self.entry.entry_id,
                    "printer_id": printer_id,
                },
            )

    def error_received(self, exc):
        _LOGGER.error("UDP error: %s", exc)

    def connection_lost(self, exc):
        _LOGGER.warning("UDP connection lost: %s", exc)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Prusa Buddy Metrics from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "transport": None,
        "known_unique_ids": set(),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    port = entry.options.get(CONF_UDP_PORT, entry.data[CONF_UDP_PORT])

    hass.config_entries.async_update_entry(
        entry, title=f"Prusa Buddy Metrics (port {port})"
    )

    protocol = PrusaBuddyUDPProtocol(hass, entry)

    try:
        transport, _ = await hass.loop.create_datagram_endpoint(
            lambda: protocol,
            local_addr=("0.0.0.0", port),
        )
        hass.data[DOMAIN][entry.entry_id]["transport"] = transport
    except OSError as err:
        _LOGGER.error("Failed to start UDP listener on port %s: %s", port, err)
        return False

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    transport = hass.data[DOMAIN][entry.entry_id].get("transport")
    if transport:
        transport.close()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
