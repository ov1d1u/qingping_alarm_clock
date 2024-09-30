from __future__ import annotations

from homeassistant.const import CONF_NAME, PERCENTAGE
from homeassistant.const import UnitOfTime
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode

from .entity import async_device_device_info_fn
from .qingping import Qingping
from .qingping.configuration import Configuration
from .qingping.events import DEVICE_CONFIG_UPDATE

async def async_setup_entry(hass, config_entry, async_add_entities):
    instance: Qingping = config_entry.runtime_data
    async_add_entities([
        QingpingSoundVolume(instance, config_entry),
        ScreenlightTime(instance, config_entry),
        DaytimeBrightness(instance, config_entry),
        NighttimeBrightness(instance, config_entry)
    ])


class QingpingSoundVolume(NumberEntity):
    def __init__(self, instance, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Volume"
        self._attr_unique_id = f"{instance.name}_volume"
        self._attr_device_class = NumberDeviceClass.VOLUME
        self._attr_mode = NumberMode.SLIDER
        self._attr_icon = "mdi:volume-high"
        self._attr_native_min_value = 1
        self._attr_native_max_value = 5
        self._attr_native_step = 1
        self._attr_native_value = 0
        instance.eventbus.add_listener(DEVICE_CONFIG_UPDATE, self.config_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def config_updated(self, config: Configuration):
        self._attr_native_value = config.sound_volume
        self.schedule_update_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        await self._instance.set_sound_volume(int(value))


class ScreenlightTime(NumberEntity):
    def __init__(self, instance, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Screen Light Time"
        self._attr_unique_id = f"{instance.name}_screen_light_time"
        self._attr_mode = NumberMode.SLIDER
        self._attr_icon = "mdi:sun-clock"
        self._attr_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_native_min_value = 1
        self._attr_native_max_value = 30
        self._attr_native_step = 1
        self._attr_native_value = 0
        instance.eventbus.add_listener(DEVICE_CONFIG_UPDATE, self.config_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def config_updated(self, config: Configuration):
        self._attr_native_value = config.screen_light_time
        self.schedule_update_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        await self._instance.set_screen_light_time(int(value))


class DaytimeBrightness(NumberEntity):
    def __init__(self, instance, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Daytime Brightness"
        self._attr_unique_id = f"{instance.name}_daytime_brightness"
        self._attr_mode = NumberMode.SLIDER
        self._attr_icon = "mdi:brightness-7"
        self._attr_unit_of_measurement = PERCENTAGE
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 10
        self._attr_native_value = 0
        instance.eventbus.add_listener(DEVICE_CONFIG_UPDATE, self.config_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def config_updated(self, config: Configuration):
        self._attr_native_value = config.daytime_brightness
        self.schedule_update_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        await self._instance.set_daytime_brightness(int(value))


class NighttimeBrightness(NumberEntity):
    def __init__(self, instance, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Night-time Brightness"
        self._attr_unique_id = f"{instance.name}_nighttime_brightness"
        self._attr_mode = NumberMode.SLIDER
        self._attr_icon = "mdi:brightness-7"
        self._attr_unit_of_measurement = PERCENTAGE
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 10
        self._attr_native_value = 0
        instance.eventbus.add_listener(DEVICE_CONFIG_UPDATE, self.config_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def config_updated(self, config: Configuration):
        self._attr_native_value = config.nighttime_brightness
        self.schedule_update_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        await self._instance.set_nighttime_brightness(int(value))