import logging
import re
import voluptuous as vol
from datetime import datetime

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util

from .qingping.util import alarm_days_from_string
from .qingping import Qingping, Alarm
from .const import (
    DOMAIN,
    SERVICE_SET_ALARM,
    SERVICE_DELETE_ALARM,
    SERVICE_GET_ALARMS,
    SERVICE_SET_TIME,
    SERVICE_SYNC_TIME,
    SERVICE_REFRESH,
    CONF_TIME,
    ALARM_SLOTS_COUNT,
    CONF_ALARM_ENABLED,
    CONF_ALARM_SLOT,
    CONF_ALARM_TIME,
    CONF_ALARM_DAYS,
    CONF_ALARM_SNOOZE,
    ATTR_ONLY_ENABLED,
)

_LOGGER = logging.getLogger(__name__)

DAYS_REGEX = re.compile(r"^(mon|tue|wed|thu|fri|sat|sun)(,(mon|tue|wed|thu|fri|sat|sun))*$")

SET_ALARM_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): str,
    vol.Required(CONF_ALARM_SLOT): vol.All(vol.Coerce(int), vol.Range(min=0, max=ALARM_SLOTS_COUNT - 1)),
    vol.Optional(CONF_ALARM_TIME): cv.time,
    vol.Optional(CONF_ALARM_DAYS): vol.All(cv.string, vol.Match(DAYS_REGEX)),
    vol.Optional(CONF_ALARM_ENABLED): cv.boolean,
    vol.Optional(CONF_ALARM_SNOOZE): cv.boolean,
})

DELETE_ALARM_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): str,
    vol.Required(CONF_ALARM_SLOT): vol.All(vol.Coerce(int), vol.Range(min=0, max=ALARM_SLOTS_COUNT - 1)),
})

GET_ALARMS_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): str,
    vol.Optional(ATTR_ONLY_ENABLED, default=False): cv.boolean
})

SET_TIME_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): str,
    vol.Required(CONF_TIME): cv.datetime
})

SYNC_TIME_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): str
})

REFRESH_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): str
})

@callback
def async_register_services(hass: HomeAssistant) -> None:
    async def async_set_alarm(call: ServiceCall) -> None:
        """Set alarm at the specified slot."""
        mac = _get_device_mac(hass, call)
        if mac is None:
            raise ServiceValidationError("Unable to resolve Bluetooth MAC from device_id")

        for entry in hass.config_entries.async_entries(DOMAIN):
            instance: Qingping = entry.runtime_data
            if instance.mac != mac:
                continue

            slot = call.data.get(CONF_ALARM_SLOT)
            is_enabled = call.data.get(CONF_ALARM_ENABLED)
            time = call.data.get(CONF_ALARM_TIME)
            days = alarm_days_from_string(call.data.get(CONF_ALARM_DAYS))
            snooze = call.data.get(CONF_ALARM_SNOOZE)

            await instance.set_alarm(
                slot,
                is_enabled,
                time,
                days,
                snooze
            )
            return

        raise ServiceValidationError(f"Qingping device with MAC {mac} is not configured")

    async def async_get_alarms(call: ServiceCall) -> ServiceResponse:
        """Get the list of alarms."""
        mac = _get_device_mac(hass, call)
        if mac is None:
            raise ServiceValidationError("Unable to resolve Bluetooth MAC from device_id")

        only_enabled = call.data.get(ATTR_ONLY_ENABLED, False)
        for entry in hass.config_entries.async_entries(DOMAIN):
            instance: Qingping = entry.runtime_data
            if instance.mac != mac:
                continue

            responseAlarms = []
            for alarm in instance.alarms:
                if not alarm.is_configured:
                    continue
                if only_enabled and not alarm.is_enabled:
                    continue

                alarm_dict = {
                    CONF_ALARM_SLOT: alarm.slot,
                    CONF_ALARM_ENABLED: alarm.is_enabled,
                    CONF_ALARM_TIME: alarm.time,
                    CONF_ALARM_DAYS: alarm.days_string,
                    CONF_ALARM_SNOOZE: alarm.snooze
                }
                responseAlarms.append(alarm_dict)

            responseAlarms.sort(key=lambda a: a[CONF_ALARM_SLOT]) # order by slot number
            return {"alarms": responseAlarms}

        raise ServiceValidationError(f"Qingping device with MAC {mac} is not configured")

    async def async_delete_alarm(call: ServiceCall) -> None:
        """Delete alarm at the specified slot."""
        mac = _get_device_mac(hass, call)
        if mac is None:
            raise ServiceValidationError("Unable to resolve Bluetooth MAC from device_id")

        for entry in hass.config_entries.async_entries(DOMAIN):
            instance: Qingping = entry.runtime_data
            if instance.mac != mac:
                continue

            slot = int(call.data[CONF_ALARM_SLOT])
            await instance.delete_alarm(slot)
            return

        raise ServiceValidationError(f"Qingping device with MAC {mac} is not configured")

    async def async_set_time(call: ServiceCall) -> None:
        """Set time"""
        mac = _get_device_mac(hass, call)
        if mac is None:
            raise ServiceValidationError("Unable to resolve Bluetooth MAC from device_id")

        for entry in hass.config_entries.async_entries(DOMAIN):
            instance: Qingping = entry.runtime_data
            if instance.mac != mac:
                continue

            dt = call.data["time"]
            timezone_offset = 0
            if dt.tzinfo is not None:
                timezone_offset = int(dt.utcoffset().total_seconds() / 60)
            timestamp = int(dt.timestamp())
            await instance.set_time(timestamp, timezone_offset)
            return

        raise ServiceValidationError(f"Qingping device with MAC {mac} is not configured")

    async def async_sync_time(call: ServiceCall) -> None:
        """Sync the clock's time with the Home Assistant instance."""
        mac = _get_device_mac(hass, call)

        for entry in hass.config_entries.async_entries(DOMAIN):
            instance: Qingping = entry.runtime_data
            if instance.mac != mac:
                continue

            dt = dt_util.now()
            timezone_offset = int(dt.utcoffset().total_seconds() / 60)
            timestamp = int(dt.timestamp())
            await instance.set_time(timestamp, timezone_offset)

    async def async_refresh(call: ServiceCall) -> None:
        """Connect to the clock to refresh data"""
        mac = _get_device_mac(hass, call)
        if mac is None:
            raise ServiceValidationError("Unable to resolve Bluetooth MAC from device_id")

        for entry in hass.config_entries.async_entries(DOMAIN):
            instance: Qingping = entry.runtime_data
            if instance.mac != mac:
                continue

            await instance.connect()
            return

        raise ServiceValidationError(f"Qingping device with MAC {mac} is not configured")

    def _get_device_mac(hass, call):
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get(call.data[ATTR_DEVICE_ID])

        if device_entry is None:
            return

        mac = None
        for connection in device_entry.connections:
            if connection[0] == CONNECTION_BLUETOOTH:
                mac = connection[1]
                break

        return mac

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ALARM,
        async_set_alarm,
        schema=SET_ALARM_SCHEMA
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_ALARMS,
        async_get_alarms,
        schema=GET_ALARMS_SCHEMA,
        supports_response=SupportsResponse.ONLY
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_ALARM,
        async_delete_alarm,
        schema=DELETE_ALARM_SCHEMA
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TIME,
        async_set_time,
        schema=SET_TIME_SCHEMA
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC_TIME,
        async_sync_time,
        schema=SYNC_TIME_SCHEMA
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        async_refresh,
        schema=REFRESH_SCHEMA
    )
