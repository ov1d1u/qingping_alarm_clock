import asyncio
from types import SimpleNamespace

import pytest

from custom_components.qingping_alarm_clock.qingping.alarm import Alarm
from custom_components.qingping_alarm_clock.qingping.qingping import (
    ALARM_SLOTS_COUNT,
    CFG_READ_CHAR,
    Qingping,
)


class _FakeServices:
    def __init__(self, available_characteristics):
        self._available_characteristics = set(available_characteristics)

    def get_characteristic(self, characteristic_uuid):
        if characteristic_uuid in self._available_characteristics:
            return object()
        return None


class _FakeClient:
    def __init__(self, services):
        self.services = services
        self._services = services
        self.is_connected = True
        self.get_services_called = False

    async def get_services(self):
        self.get_services_called = True
        return self._services


@pytest.fixture
def qingping_instance():
    return Qingping(hass=object(), mac="AA:BB:CC:DD:EE:FF", name="Test Clock")


@pytest.mark.asyncio
async def test_get_configuration_clears_event_before_wait(qingping_instance):
    write_calls = []

    async def fake_write_config(data):
        write_calls.append(data)

    qingping_instance.client = SimpleNamespace(is_connected=True)
    qingping_instance._write_config = fake_write_config
    qingping_instance._configuration_event.set()

    async def set_event_after_tick():
        await asyncio.sleep(0)
        qingping_instance._configuration_event.set()

    task = asyncio.create_task(set_event_after_tick())
    await qingping_instance.get_configuration()
    await task

    assert write_calls == [b"\x01\x02"]


@pytest.mark.asyncio
async def test_ensure_required_characteristics_uses_cached_services(qingping_instance):
    from custom_components.qingping_alarm_clock.qingping.qingping import REQUIRED_CHARS

    qingping_instance.client = _FakeClient(services=_FakeServices(REQUIRED_CHARS))

    await qingping_instance._ensure_required_characteristics()

    assert qingping_instance.client.get_services_called is False


@pytest.mark.asyncio
async def test_ensure_required_characteristics_fetches_services_when_missing(qingping_instance):
    from custom_components.qingping_alarm_clock.qingping.qingping import REQUIRED_CHARS

    qingping_instance.client = _FakeClient(services=_FakeServices(REQUIRED_CHARS))
    qingping_instance.client.services = None

    await qingping_instance._ensure_required_characteristics()

    assert qingping_instance.client.get_services_called is True


@pytest.mark.asyncio
async def test_alarm_notification_sets_event_only_after_full_set(qingping_instance):
    sender = SimpleNamespace(uuid=CFG_READ_CHAR)

    received_updates = []

    async def alarms_listener(alarms):
        received_updates.append(alarms)

    qingping_instance.eventbus.add_listener(
        "qingping_alarms_updated",
        alarms_listener,
    )

    first_payload = b"\x11\x06\x00" + bytes.fromhex("ffffffffff") + bytes.fromhex("ffffffffff") + bytes.fromhex("ffffffffff")
    await qingping_instance._notification_handler(sender, first_payload)

    assert qingping_instance._alarms_event.is_set() is False

    for slot_offset in (3, 6, 9, 12, 15, 18):
        payload = b"\x11\x06" + bytes([slot_offset])
        payload += bytes.fromhex("ffffffffff")
        payload += bytes.fromhex("ffffffffff")
        payload += bytes.fromhex("ffffffffff")
        await qingping_instance._notification_handler(sender, payload)

    await asyncio.sleep(0)

    assert qingping_instance._alarms_event.is_set() is True
    assert len(qingping_instance.alarms) == ALARM_SLOTS_COUNT
    assert all(isinstance(alarm, Alarm) for alarm in qingping_instance.alarms)
    assert len(received_updates) == 1


@pytest.mark.asyncio
async def test_malformed_alarm_payload_is_ignored(qingping_instance):
    sender = SimpleNamespace(uuid=CFG_READ_CHAR)

    payload = b"\x11\x06\x00\xff\xff"
    await qingping_instance._notification_handler(sender, payload)

    assert qingping_instance._alarms_event.is_set() is False
    assert qingping_instance.alarms == []
