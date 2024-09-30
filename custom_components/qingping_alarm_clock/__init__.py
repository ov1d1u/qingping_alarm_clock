"""The Qingping CGD1 Alarm Clock integration."""
from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant, callback, ServiceCall
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.match import ADDRESS, BluetoothCallbackMatcher

from .services import async_register_services
from .qingping import Qingping
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.TIME,
    Platform.SELECT]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry
) -> bool:
    """Set up Qingping CGD1 Alarm Clock from a config entry."""

    mac = entry.options.get(CONF_MAC, None) or entry.data.get(CONF_MAC, None)
    name = entry.options.get(CONF_NAME, None) or entry.data.get(CONF_NAME, None)

    instance = Qingping(hass, mac, name)
    entry.runtime_data = instance

    async_register_services(hass)

    async def _connect_if_needed():
        await instance.connect_if_needed()

    @callback
    def _async_discovered_device(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange
    ):
        """Subscribe to bluetooth changes."""
        _LOGGER.debug("New service_info: %s", service_info)
        hass.loop.create_task(_connect_if_needed())

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_discovered_device,
            BluetoothCallbackMatcher({ADDRESS: mac}),
            bluetooth.BluetoothScanningMode.PASSIVE
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        instance: Qingping = entry.runtime_data
        await instance.disconnect()
    return unload_ok

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    instance: Qingping = entry.runtime_data
    if entry.title != instance.name:
        await hass.config_entries.async_reload(entry.entry_id)