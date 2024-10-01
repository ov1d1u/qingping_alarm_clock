import asyncio
import logging
import time
from bleak import BleakClient
from datetime import time as dtime

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.components.bluetooth import (
    async_ble_device_from_address
)

from .configuration import Configuration, Language
from .util import updates_configuration, ensure_alarms
from .alarm import Alarm, AlarmDay
from .eventbus import EventBus
from .exceptions import NotConnectedError
from ..const import ALARM_SLOTS_COUNT, DISCONNECT_DELAY
from .events import (
    DEVICE_CONNECT,
    DEVICE_DISCONNECT,
    DEVICE_CONFIG_UPDATE,
    ALARMS_UPDATE
)

_LOGGER = logging.getLogger(__name__)

MAIN_CHAR       = "00000001-0000-1000-8000-00805f9b34fb"
CFG_WRITE_CHAR  = "0000000B-0000-1000-8000-00805f9b34fb"
CFG_READ_CHAR   = "0000000C-0000-1000-8000-00805f9b34fb"

AUTH_STEP_1 = bytes.fromhex("1101ea600e964287ea7d17894900da6174bd")
AUTH_STEP_2 = bytes.fromhex("1102ea600e964287ea7d17894900da6174bd")


class Qingping:
    client = None
    configuration = None
    alarms: list[Alarm] = []
    eventbus = EventBus()

    _connect_lock = asyncio.Lock()
    _configuration_event = asyncio.Event()
    _alarms_event = asyncio.Event()
    _disconnect_task = None

    def __init__(self, hass: HomeAssistant, mac: str, name: str):
        """Initialize the Qingping CGD1 Alarm Clock."""
        self.hass = hass
        self.mac = mac
        self.name = name

    async def connect(self) -> bool:
        async with self._connect_lock:
            if self.client and self.client.is_connected:
                return True

            device = async_ble_device_from_address(self.hass, self.mac, connectable=True)
            self.client = BleakClient(device)

            _LOGGER.debug(f"Connecting to {self.mac}...")
            try:
                await self.client.connect()
            except Exception as e:
                _LOGGER.debug(f"Failed to connect to {self.mac}: {e}")
                return False

            await asyncio.sleep(2.0)  # give some time for service discovery

            _LOGGER.debug(f"Connected to {self.mac}, authenticating...")

            # Step 1 auth
            await self._write_gatt_char(MAIN_CHAR, AUTH_STEP_1)

            # Step 2 auth
            await self._write_gatt_char(MAIN_CHAR, AUTH_STEP_2)

            self.eventbus.send(DEVICE_CONNECT, self)

            # Read configuration
            _LOGGER.debug("Reading configuration...")
            await self.client.start_notify(CFG_READ_CHAR, self._notification_handler)
            await self.get_configuration()

            # Read alarms
            _LOGGER.debug("Reading alarms...")
            await self.get_alarms()

            return True

    async def connect_if_needed(self) -> bool:
        if not self.configuration or self.configuration.is_expired:
            return await self.connect()

        return False

    async def disconnect(self) -> bool:
        if self.client and self.client.is_connected:
            _LOGGER.debug(f"Disconnecting from {self.mac}...")
            await self.client.disconnect()
            self.eventbus.send(DEVICE_DISCONNECT, self)
            self.client = None
            return True

        return False

    async def delayed_disconnect(self):
        if not self.client.is_connected:
            return

        try:
            await asyncio.sleep(DISCONNECT_DELAY)
            await self.disconnect()
            if self._disconnect_task:
                self._disconnect_task.cancel()
                self._disconnect_task = None
            _LOGGER.debug(f"Disconnected from {self.mac}")
        except Exception as e:
            _LOGGER.debug(f"Failed to disconnect. Error: {e}")

    async def get_configuration(self):
        if self.client and self.client.is_connected:
            await self._write_config(b"\x01\x02")
            await self._configuration_event.wait()
        else:
            raise NotConnectedError("Not connected")

    async def set_configuration(self, configuration: Configuration):
        await self._write_config(configuration.to_bytes())
        await self._write_config(b"\x01\x02")

    async def set_time(self, timestamp: int, timezone_offset: int | None = None):
        start_time = time.time()

        await self._ensure_configuration()

        # Account for time passed while connecting
        timestamp = int(timestamp + (time.time() - start_time))

        timestamp_bytes = self._get_timestamp_bytes(timestamp)
        await self._write_gatt_char(MAIN_CHAR, timestamp_bytes)

        if timezone_offset is not None and \
            self.configuration.timezone_offset != timezone_offset:

            self.configuration.timezone_offset = timezone_offset
            await self.set_configuration(self.configuration)

    async def get_alarms(self):
        if self.client and self.client.is_connected:
            await self._write_config(b"\x01\x06")
            await self._alarms_event.wait()
        else:
            raise NotConnectedError("Not connected")

    @ensure_alarms
    async def set_alarm(
        self,
        slot: int,
        is_enabled: bool | None,
        time: dtime | None,
        days: set[AlarmDay] | None
    ) -> bool:
        if slot >= 0 and slot < ALARM_SLOTS_COUNT:
            alarm: Alarm = self.alarms[slot]
            if is_enabled is not None:
                alarm.is_enabled = is_enabled
            if time is not None:
                alarm.time = time
            if days is not None:
                alarm.days = days

            if not alarm.is_configured:
                raise ServiceValidationError("Alarm not configured.")

            if not self.client or not self.client.is_connected:
                await self.connect()

            await self._write_config(alarm.to_bytes())
            await self.get_alarms()
            return True

        return False

    @ensure_alarms
    async def delete_alarm(self, slot: int) -> bool:
        if slot >= 0 and slot < ALARM_SLOTS_COUNT:
            alarm: Alarm = self.alarms[slot]
            alarm.deactivate()

            if self.client and self.client.is_connected:
                await self._write_config(alarm.to_bytes())
                await self.get_alarms()
                return True
            else:
                raise NotConnectedError("Not connected")

    @updates_configuration
    async def enable_alarms(self, is_enabled: bool):
        self.configuration.alarms_on = is_enabled
        await self._write_config(self.configuration.to_bytes())

    @updates_configuration
    async def set_sound_volume(self, volume: int):
        self.configuration.sound_volume = volume
        await self._write_config(self.configuration.to_bytes())
        await self._write_config(b"\x01\x04")

    @updates_configuration
    async def set_screen_light_time(self, _time: int):
        self.configuration.screen_light_time = _time
        await self._write_config(self.configuration.to_bytes())

    @updates_configuration
    async def set_daytime_brightness(self, brightness: int):
        self.configuration.daytime_brightness = brightness
        await self._write_config(self.configuration.to_bytes())
        await self._write_config(bytes([0x02, 0x03, brightness//10]))

    @updates_configuration
    async def set_nighttime_brightness(self, brightness: int):
        self.configuration.nighttime_brightness = brightness
        await self._write_config(self.configuration.to_bytes())
        await self._write_config(bytes([0x02, 0x03, brightness//10]))

    @updates_configuration
    async def set_nighttime_start_time(self, _time: dtime):
        self.configuration.night_time_start_time = _time
        await self._write_config(self.configuration.to_bytes())

    @updates_configuration
    async def set_nighttime_end_time(self, _time: dtime):
        self.configuration.night_time_end_time = _time
        await self._write_config(self.configuration.to_bytes())

    @updates_configuration
    async def set_night_mode(self, is_night_mode: bool):
        self.configuration.night_mode_enabled = is_night_mode
        await self._write_config(self.configuration.to_bytes())

    @updates_configuration
    async def set_language(self, language: Language):
        self.configuration.language = language
        await self._write_config(self.configuration.to_bytes())

    @updates_configuration
    async def set_24h_time_format(self, is_24h: bool):
        self.configuration.use_24h_format = is_24h
        await self._write_config(self.configuration.to_bytes())

    @updates_configuration
    async def set_uses_celsius(self, is_celsius: bool):
        self.configuration.use_celsius = is_celsius
        await self._write_config(self.configuration.to_bytes())

    async def _ensure_connected(self):
        if not self.client or not self.client.is_connected:
            await self.connect()

    async def _ensure_configuration(self):
        if not self.configuration or self.configuration.is_expired:
            if not self.client or not self.client.is_connected:
                await self.connect()

            await self.get_configuration()

    async def _ensure_alarms(self):
        if not self.alarms:
            if not self.client or not self.client.is_connected:
                await self.connect()

            await self.get_alarms()

    async def _write_config(self, data: bytes):
        if self.client and self.client.is_connected:
            await self._write_gatt_char(CFG_WRITE_CHAR, data)

            loop = asyncio.get_running_loop()
            if self._disconnect_task is not None:
                self._disconnect_task.cancel()
            self._disconnect_task = loop.create_task(self.delayed_disconnect())
        else:
            raise NotConnectedError("Not connected")

    async def _write_gatt_char(self, uuid: str, data: bytes):
        if self.client and self.client.is_connected:
            _LOGGER.debug(f">> {uuid}: {data.hex()}")
            await self.client.write_gatt_char(uuid, data)
        else:
            raise NotConnectedError("Not connected")

    def _get_timestamp_bytes(self, timestamp: int):
        timestamp_bytes = [0] * 6
        timestamp_bytes[0] = 0x05
        timestamp_bytes[1] = 0x09
        timestamp_bytes[2] = (timestamp >> 0) & 0xFF
        timestamp_bytes[3] = (timestamp >> 8) & 0xFF
        timestamp_bytes[4] = (timestamp >> 16) & 0xFF
        timestamp_bytes[5] = (timestamp >> 24) & 0xFF

        return bytes(timestamp_bytes)

    async def _notification_handler(self, sender, data):
        if sender.uuid.lower() == CFG_READ_CHAR.lower():
            _LOGGER.debug(f"<< {sender.uuid}: {data.hex()}")
            if data.startswith(b"\x13\x02"):
                _LOGGER.debug(f"Got configuration bytes: {data.hex()}")
                self.configuration = Configuration(data)

                self._configuration_event.set()
                self.eventbus.send(DEVICE_CONFIG_UPDATE, self.configuration)
            elif data.startswith(b"\x11\x06") and len(data) == 18:
                _LOGGER.debug(f"Got alarms bytes: {data.hex()}")
                slot_offset = data[2]
                if slot_offset == 0:
                    self.alarms = []

                self.alarms.append(Alarm(slot_offset, data[3:8]))
                self.alarms.append(Alarm(slot_offset + 1, data[8:13]))
                self.alarms.append(Alarm(slot_offset + 2, data[13:18]))

                self._alarms_event.set()
                self.eventbus.send(ALARMS_UPDATE, self.alarms)
