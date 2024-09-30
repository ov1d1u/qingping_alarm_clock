import logging
import re
import voluptuous as vol
from datetime import datetime
import pytz

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.const import ATTR_DEVICE_ID

from .qingping.util import alarm_days_from_string
from .qingping import Qingping
from .const import (
    DOMAIN,
    SERVICE_SET_ALARM,
    SERVICE_DELETE_ALARM,
    SERVICE_SET_TIME,
    SERVICE_REFRESH,
    CONF_TIME,
    CONF_TIMEZONE,
    ALARM_SLOTS_COUNT,
    CONF_ALARM_ENABLED,
    CONF_ALARM_SLOT,
    CONF_ALARM_TIME,
    CONF_ALARM_DAYS,
)

_LOGGER = logging.getLogger(__name__)

DAYS_REGEX = re.compile(r"^(mon|tue|wed|thu|fri|sat|sun)(,(mon|tue|wed|thu|fri|sat|sun))*$")

SET_ALARM_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): str,
    vol.Required(CONF_ALARM_SLOT): vol.All(vol.Coerce(int), vol.Range(min=0, max=ALARM_SLOTS_COUNT)),
    vol.Required(CONF_ALARM_TIME): cv.time,
    vol.Required(CONF_ALARM_DAYS): vol.All(cv.string, vol.Match(DAYS_REGEX)),
    vol.Required(CONF_ALARM_ENABLED): cv.boolean,
})

DELETE_ALARM_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): str,
    vol.Required(CONF_ALARM_SLOT): vol.All(vol.Coerce(int), vol.Range(min=0, max=ALARM_SLOTS_COUNT)),
})

SET_TIME_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): str,
    vol.Required(CONF_TIME): cv.datetime,
    vol.Required(CONF_TIMEZONE): cv.string
})

REFRESH_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): str
})

@callback
def async_register_services(hass: HomeAssistant) -> None:
    async def async_set_alarm(call: ServiceCall) -> None:
        """Set alarm at the specified slot."""
        mac = _get_device_mac(hass, call)

        for entry in hass.config_entries.async_entries(DOMAIN):
            instance: Qingping = entry.runtime_data
            if instance.mac != mac:
                continue

            slot = int(call.data[CONF_ALARM_SLOT])
            time = call.data[CONF_ALARM_TIME]
            days = alarm_days_from_string(call.data[CONF_ALARM_DAYS])

            await instance.set_alarm(
                slot,
                call.data[CONF_ALARM_ENABLED],
                time,
                days
            )

    async def async_delete_alarm(call: ServiceCall) -> None:
        """Delete alarm at the specified slot."""
        mac = _get_device_mac(hass, call)

        for entry in hass.config_entries.async_entries(DOMAIN):
            instance: Qingping = entry.runtime_data
            if instance.mac != mac:
                continue

            slot = int(call.data[CONF_ALARM_SLOT])
            await instance.delete_alarm(slot)

    async def async_set_time(call: ServiceCall) -> None:
        """Set time"""
        mac = _get_device_mac(hass, call)

        for entry in hass.config_entries.async_entries(DOMAIN):
            instance: Qingping = entry.runtime_data
            if instance.mac != mac:
                continue

            timezone = await hass.async_add_executor_job(pytz.timezone, call.data["timezone"])
            timezone_offset = int(timezone.utcoffset(datetime.now()).total_seconds() / 60)
            naive_dt = call.data["time"]
            localized_dt = timezone.localize(naive_dt)
            utc_dt = localized_dt.astimezone(pytz.utc)
            timestamp = int(utc_dt.timestamp())
            await instance.set_time(timestamp, timezone_offset)

    async def async_refresh(call: ServiceCall) -> None:
        """Connect to the clock to refresh data"""
        mac = _get_device_mac(hass, call)

        for entry in hass.config_entries.async_entries(DOMAIN):
            instance: Qingping = entry.runtime_data
            if instance.mac != mac:
                continue

            await instance.connect()

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
        SERVICE_REFRESH,
        async_refresh,
        schema=REFRESH_SCHEMA
    )
