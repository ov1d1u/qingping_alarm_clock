from types import SimpleNamespace

import pytest

from custom_components.qingping_alarm_clock.binary_sensor import QingpingConnectedBinarySensor
from custom_components.qingping_alarm_clock.qingping import Qingping
from custom_components.qingping_alarm_clock.qingping.configuration import Configuration


@pytest.mark.asyncio
async def test_connected_binary_sensor_syncs_initial_connected_state():
    instance = Qingping(hass=object(), mac="AA:BB:CC:DD:EE:FF", name="Test Clock")
    instance.client = SimpleNamespace(is_connected=True)

    config_entry = SimpleNamespace(data={"name": "My Clock"})
    sensor = QingpingConnectedBinarySensor(instance, config_entry)

    assert sensor._attr_is_on is True
    assert sensor._attr_icon == "mdi:bluetooth-connect"


@pytest.mark.asyncio
async def test_connected_binary_sensor_resyncs_on_configuration_update():
    instance = Qingping(hass=object(), mac="AA:BB:CC:DD:EE:FF", name="Test Clock")
    instance.client = SimpleNamespace(is_connected=False)

    config_entry = SimpleNamespace(data={"name": "My Clock"})
    sensor = QingpingConnectedBinarySensor(instance, config_entry)

    assert sensor._attr_is_on is False

    instance.client = SimpleNamespace(is_connected=True)
    config = Configuration(bytes([0x13, 0x02, 3, 0xFF, 0xFF, 0, 0, 1, 0x11, 21, 0, 6, 0, 1, 0]))
    await sensor.on_configuration_update(config)

    assert sensor._attr_is_on is True
    assert sensor._attr_icon == "mdi:bluetooth-connect"


@pytest.mark.asyncio
async def test_connected_binary_sensor_unique_id_uses_mac_not_name():
    instance = Qingping(hass=object(), mac="AA:BB:CC:DD:EE:FF", name="Clock Runtime Name")
    config_entry = SimpleNamespace(data={"name": "Friendly Name"})

    sensor = QingpingConnectedBinarySensor(instance, config_entry)

    assert sensor._attr_unique_id == "aabbccddeeff_is_connected"
