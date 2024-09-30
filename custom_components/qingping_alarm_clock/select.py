from __future__ import annotations
from enum import Enum

from homeassistant.const import CONF_NAME
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import DeviceInfo

from .entity import async_device_device_info_fn
from .qingping import Qingping
from .qingping.configuration import Configuration, Language
from .qingping.events import DEVICE_CONFIG_UPDATE

async def async_setup_entry(hass, config_entry, async_add_entities):
    instance: Qingping = config_entry.runtime_data
    async_add_entities([
        LanguageSelect(instance, config_entry),
        TimeFormatSelect(instance, config_entry),
        TemperatureUnitSelect(instance, config_entry)
    ])


class TimeFormat(Enum):
    _24H = "24h"
    _12H = "12h"


class TemperatureUnit(Enum):
    C = "Celsius"
    F = "Fahrenheit"


class LanguageSelect(SelectEntity):
    def __init__(self, instance, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Language"
        self._attr_unique_id = f"{instance.name}_language"
        self._attr_icon = "mdi:language"
        self._attr_options = [Language.ZH.value, Language.EN.value]
        self._attr_current_option = None
        instance.eventbus.add_listener(DEVICE_CONFIG_UPDATE, self.config_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def async_select_option(self, option: str) -> None:
        language = Language(option)
        await self._instance.set_language(language)

    async def async_set_value(self, value: str) -> None:
        language = Language(value)
        await self._instance.set_language(language)

    async def config_updated(self, config: Configuration):
        self._attr_current_option = config.language.value


class TimeFormatSelect(SelectEntity):
    def __init__(self, instance, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Time Format"
        self._attr_unique_id = f"{instance.name}_time_format"
        self._attr_icon = "mdi:clock"
        self._attr_options = [TimeFormat._24H.value, TimeFormat._12H.value]
        self._attr_current_option = None
        instance.eventbus.add_listener(DEVICE_CONFIG_UPDATE, self.config_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def async_select_option(self, option: str) -> None:
        if option == TimeFormat._24H.value:
            await self._instance.set_24h_time_format(True)
        else:
            await self._instance.set_24h_time_format(False)

    async def config_updated(self, config: Configuration):
        self._attr_current_option = "24h" if config.use_24h_format else "12h"


class TemperatureUnitSelect(SelectEntity):
    def __init__(self, instance, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Temperature Unit"
        self._attr_unique_id = f"{instance.name}_temperature_unit"
        self._attr_icon = "mdi:thermometer"
        self._attr_options = [TemperatureUnit.C.value, TemperatureUnit.F.value]
        self._attr_current_option = None
        instance.eventbus.add_listener(DEVICE_CONFIG_UPDATE, self.config_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def async_select_option(self, option: str) -> None:
        if option == TemperatureUnit.C.value:
            await self._instance.set_uses_celsius(True)
        else:
            await self._instance.set_uses_celsius(False)

    async def config_updated(self, config: Configuration):
        self._attr_current_option = \
            TemperatureUnit.C.value if config.use_celsius else TemperatureUnit.F.value
