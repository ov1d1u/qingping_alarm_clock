from __future__ import annotations
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH

from .qingping import Qingping

@callback
def async_device_device_info_fn(qingping: Qingping, name: str) -> DeviceInfo:
    return DeviceInfo(
        connections={(CONNECTION_BLUETOOTH, qingping.mac)},
        manufacturer="Qingping",
        model="CGD1",
        name=name
    )