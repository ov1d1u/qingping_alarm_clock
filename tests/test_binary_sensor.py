from types import SimpleNamespace

import pytest

from custom_components.qingping_alarm_clock.binary_sensor import QingpingConnectedBinarySensor
from custom_components.qingping_alarm_clock.qingping import Qingping


def _make_sensor(connected=False):
    instance = Qingping(hass=object(), mac="AA:BB:CC:DD:EE:FF", name="Test Clock")
    instance._connected = connected
    config_entry = SimpleNamespace(data={"name": "My Clock"})
    return instance, QingpingConnectedBinarySensor(instance, config_entry)


@pytest.mark.asyncio
async def test_connected_binary_sensor_syncs_initial_connected_state():
    _, sensor = _make_sensor(connected=True)

    assert sensor._attr_is_on is True
    assert sensor._attr_icon == "mdi:bluetooth-connect"


@pytest.mark.asyncio
async def test_connected_binary_sensor_follows_connect_and_disconnect_events():
    instance, sensor = _make_sensor(connected=False)
    assert sensor._attr_is_on is False

    await sensor.on_connect(instance)
    assert sensor._attr_is_on is True
    assert sensor._attr_icon == "mdi:bluetooth-connect"

    await sensor.on_disconnect(instance)
    assert sensor._attr_is_on is False
    assert sensor._attr_icon == "mdi:bluetooth-off"


@pytest.mark.asyncio
async def test_connected_binary_sensor_trusts_connect_event_over_stale_client():
    # Regression: client.is_connected can momentarily report False right after a
    # connection is established. The connect event must still turn the sensor on.
    instance, sensor = _make_sensor(connected=False)
    instance.client = None

    await sensor.on_connect(instance)
    assert sensor._attr_is_on is True


@pytest.mark.asyncio
async def test_connected_binary_sensor_unique_id_uses_mac_not_name():
    instance = Qingping(hass=object(), mac="AA:BB:CC:DD:EE:FF", name="Clock Runtime Name")
    config_entry = SimpleNamespace(data={"name": "Friendly Name"})

    sensor = QingpingConnectedBinarySensor(instance, config_entry)

    assert sensor._attr_unique_id == "aabbccddeeff_is_connected"
