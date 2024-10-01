from __future__ import annotations
from typing import Any

from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.switch import SwitchEntity

from .qingping import Qingping
from .qingping.alarm import Alarm
from .entity import async_device_device_info_fn
from .qingping.configuration import Configuration
from .qingping.events import ALARMS_UPDATE, DEVICE_CONFIG_UPDATE

async def async_setup_entry(hass, config_entry, async_add_entities):
    instance: Qingping = config_entry.runtime_data
    async_add_entities([
        QingpingAlarmsSwitch(instance, config_entry),
        QingpingNightModeSwitch(instance, config_entry)
    ])


class QingpingAlarmsSwitch(SwitchEntity):
    def __init__(self, instance, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Alarms Enabled"
        self._attr_unique_id = f"{instance.name}_alarms_enabled"
        self._attr_is_on = None
        self._attr_icon = "mdi:alarm-check"
        self._attr_extra_state_attributes = {}

        instance.eventbus.add_listener(DEVICE_CONFIG_UPDATE, self.config_updated)
        instance.eventbus.add_listener(ALARMS_UPDATE, self.alarms_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def async_turn_on(self, **kwargs):
        await self._instance.enable_alarms(True)

    async def async_turn_off(self, **kwargs):
        await self._instance.enable_alarms(False)

    async def config_updated(self, config: Configuration):
        self._attr_is_on = config.alarms_on
        self.async_write_ha_state()

    async def alarms_updated(self, alarms: list[Alarm]):
        self._attr_extra_state_attributes = {}
        for alarm in alarms:
            if alarm.is_configured:
                alarm_dict = {}
                alarm_dict["is_on"] = alarm.is_enabled
                alarm_dict["time"] = alarm.time
                alarm_dict["days"] = alarm.days_string
                self._attr_extra_state_attributes[f"alarm_{alarm.slot}"] = alarm_dict
        self.async_write_ha_state()


class QingpingNightModeSwitch(SwitchEntity):
    def __init__(self, instance, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Night Mode Enabled"
        self._attr_unique_id = f"{instance.name}_night_mode_enabled"
        self._attr_is_on = None
        self._attr_icon = "mdi:sun-clock"
        self._attr_extra_state_attributes = {}

        instance.eventbus.add_listener(DEVICE_CONFIG_UPDATE, self.config_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def async_turn_on(self, **kwargs):
        await self._instance.set_night_mode(True)

    async def async_turn_off(self, **kwargs):
        await self._instance.set_night_mode(False)

    async def config_updated(self, config: Configuration):
        self._attr_is_on = config.night_mode_enabled
        self.async_write_ha_state()