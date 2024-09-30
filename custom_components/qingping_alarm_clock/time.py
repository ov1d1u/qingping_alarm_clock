from __future__ import annotations
from datetime import time

from homeassistant.const import CONF_NAME
from homeassistant.components.time import TimeEntity
from homeassistant.helpers.entity import DeviceInfo

from .entity import async_device_device_info_fn
from .qingping import Qingping
from .qingping.configuration import Configuration
from .qingping.events import DEVICE_CONFIG_UPDATE

async def async_setup_entry(hass, config_entry, async_add_entities):
    instance: Qingping = config_entry.runtime_data
    async_add_entities([
        NighttimeStart(instance, config_entry),
        NighttimeEnd(instance, config_entry)
    ])


class NighttimeStart(TimeEntity):
    def __init__(self, instance, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Night Start Time"
        self._attr_unique_id = f"{instance.name}_nighttime_start_time"
        self._attr_icon = "mdi:clock-in"
        self._attr_native_value = None
        instance.eventbus.add_listener(DEVICE_CONFIG_UPDATE, self.config_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def config_updated(self, config: Configuration):
        self._attr_native_value = config.night_time_start_time
        self.schedule_update_ha_state()

    async def async_set_value(self, value: time) -> None:
        await self._instance.set_nighttime_start_time(value)


class NighttimeEnd(TimeEntity):
    def __init__(self, instance, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Night End Time"
        self._attr_unique_id = f"{instance.name}_nighttime_end_time"
        self._attr_icon = "mdi:clock-out"
        self._attr_native_value = None
        instance.eventbus.add_listener(DEVICE_CONFIG_UPDATE, self.config_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def config_updated(self, config: Configuration):
        self._attr_native_value = config.night_time_end_time
        self.schedule_update_ha_state()

    async def async_set_value(self, value: time) -> None:
        await self._instance.set_nighttime_end_time(value)
