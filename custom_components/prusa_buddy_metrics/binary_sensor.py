"""Binary sensor platform for Prusa Buddy Metrics."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DOMAIN, UNAVAILABLE_TIMEOUT
from . import SIGNAL_NEW_METRIC

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""

    @callback
    def handle_new_metric(data: dict):
        if data["entry_id"] != entry.entry_id:
            return
        if not data["is_binary"]:
            return

        known = hass.data[DOMAIN][entry.entry_id]["known_unique_ids"]
        unique_id = data["unique_id"]

        if unique_id not in known:
            known.add(unique_id)
            entity = PrusaBuddyMetricBinarySensor(entry, data)
            async_add_entities([entity])
            _LOGGER.debug("Registered new binary sensor: %s", data["name"])
        else:
            from homeassistant.helpers.dispatcher import async_dispatcher_send
            async_dispatcher_send(hass, f"{DOMAIN}_update_{unique_id}", data)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_METRIC, handle_new_metric)
    )


class PrusaBuddyMetricBinarySensor(BinarySensorEntity):
    """A single binary metric from a Prusa Buddy printer."""

    def __init__(self, entry: ConfigEntry, data: dict):
        self._entry = entry
        self._unique_id = data["unique_id"]
        self._printer_id = data["printer_id"]
        self._attr_name = data["name"]
        self._attr_unique_id = data["unique_id"]
        self._attr_is_on = bool(data["value"])
        self._attr_extra_state_attributes = data.get("extra_attrs", {})
        self._attr_available = True
        self._last_updated = dt_util.utcnow()
        self._unsub_update = None
        self._unsub_timer = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._printer_id)},
            name=f"Prusa Buddy {self._printer_id}",
            manufacturer="Prusa Research",
            model="Buddy",
        )

    async def async_added_to_hass(self):
        """Subscribe to value updates and start availability timer."""

        @callback
        def update_value(data):
            if isinstance(data, dict):
                self._attr_is_on = bool(data["value"])
                self._attr_extra_state_attributes = data.get("extra_attrs", {})
            else:
                self._attr_is_on = bool(data)
            self._attr_available = True
            self._last_updated = dt_util.utcnow()
            self.async_write_ha_state()

        self._unsub_update = async_dispatcher_connect(
            self.hass, f"{DOMAIN}_update_{self._unique_id}", update_value
        )

        @callback
        def check_availability(_now):
            elapsed = (dt_util.utcnow() - self._last_updated).total_seconds()
            if elapsed > UNAVAILABLE_TIMEOUT and self._attr_available:
                self._attr_available = False
                self.async_write_ha_state()

        self._unsub_timer = async_track_time_interval(
            self.hass, check_availability, timedelta(seconds=60)
        )

    async def async_will_remove_from_hass(self):
        if self._unsub_update:
            self._unsub_update()
        if self._unsub_timer:
            self._unsub_timer()
