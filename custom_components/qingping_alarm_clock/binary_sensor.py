from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import EntityCategory, DeviceInfo

from .entity import async_device_device_info_fn
from .qingping import Qingping
from .qingping.events import DEVICE_DISCONNECT, DEVICE_CONNECT

async def async_setup_entry(hass, config_entry, async_add_entities):
    instance: Qingping = config_entry.runtime_data
    async_add_entities([
        QingpingConnectedBinarySensor(instance, config_entry)
    ])


class QingpingConnectedBinarySensor(BinarySensorEntity):
    """Representation of a Qingping Connected Binary Sensor."""

    def __init__(self, instance: Qingping, config_entry: ConfigEntry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Connected"
        self._attr_unique_id = f"{config_entry.data[CONF_NAME]}_is_connected"
        self._attr_device_class = "connectivity"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_is_on = False
        self._attr_icon = "mdi:bluetooth-off"

        instance.eventbus.add_listener(DEVICE_CONNECT, self.on_connect)
        instance.eventbus.add_listener(DEVICE_DISCONNECT, self.on_disconnect)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def on_connect(self, instance: Qingping):
        self._attr_is_on = True
        self._attr_icon = "mdi:bluetooth-connect"
        self.schedule_update_ha_state()

    async def on_disconnect(self, instance: Qingping):
        self._attr_is_on = False
        self._attr_icon = "mdi:bluetooth-off"
        self.schedule_update_ha_state()
