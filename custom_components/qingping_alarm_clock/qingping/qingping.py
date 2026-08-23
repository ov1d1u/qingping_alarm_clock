import asyncio
import logging
import time
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from datetime import time as dtime

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.components.bluetooth import (
    async_ble_device_from_address
)

from .configuration import Configuration, Language
from .util import updates_configuration
from .alarm import Alarm, AlarmDay
from .eventbus import EventBus
from .exceptions import NotConnectedError
from ..const import (
    ALARM_SLOTS_COUNT,
    DISCONNECT_DELAY,
    CONNECTION_TIMEOUT,
    RETRY_INTERVAL,
)
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
REQUIRED_CHARS = (MAIN_CHAR, CFG_WRITE_CHAR, CFG_READ_CHAR)
EMPTY_ALARM_BYTES = bytes.fromhex("ffffffffff")

AUTH_STEP_1 = bytes.fromhex("1101ea600e964287ea7d17894900da6174bd")
AUTH_STEP_2 = bytes.fromhex("1102ea600e964287ea7d17894900da6174bd")


class Qingping:
    def __init__(self, hass: HomeAssistant, mac: str, name: str):
        """Initialize the Qingping CGD1 Alarm Clock."""
        self.hass = hass
        self.mac = mac
        self.name = name
        self.client = None
        self.configuration = None
        self.alarms: list[Alarm] = []
        self.eventbus = EventBus()
        self._connect_lock = asyncio.Lock()
        self._configuration_event = asyncio.Event()
        self._alarms_event = asyncio.Event()
        self._disconnect_task = None
        self._notify_started = False
        self._alarm_map: dict[int, Alarm] = {}

    @staticmethod
    def _empty_alarm(slot: int) -> Alarm:
        return Alarm(slot, EMPTY_ALARM_BYTES)

    def _finalize_alarms_from_map(self):
        self.alarms = [
            self._alarm_map.get(index, self._empty_alarm(index))
            for index in range(ALARM_SLOTS_COUNT)
        ]
        if not self._alarms_event.is_set():
            self._alarms_event.set()
        self.eventbus.send(ALARMS_UPDATE, self.alarms)

    async def connect(self) -> bool:
        async with self._connect_lock:
            if self.client and self.client.is_connected:
                return True

            device = async_ble_device_from_address(self.hass, self.mac, connectable=True)
            if device is None:
                _LOGGER.error(f"No adapters can reach the device with address {self.mac}")
                return False

            _LOGGER.debug(f"Connecting to {self.mac}...")
            try:
                self.client = await establish_connection(
                    BleakClient,
                    device,
                    self.name,
                    disconnected_callback=self._on_disconnect,
                )
            except Exception as e:
                _LOGGER.debug(f"Failed to connect to {self.mac}: {e}")
                return False

            try:
                await self._ensure_required_characteristics()

                _LOGGER.debug(f"Connected to {self.mac}, authenticating...")

                if not self._notify_started:
                    await self.client.start_notify(CFG_READ_CHAR, self._notification_handler)
                    self._notify_started = True

                # Step 1 auth
                await self._write_gatt_char(MAIN_CHAR, AUTH_STEP_1)

                # Step 2 auth
                await self._write_gatt_char(MAIN_CHAR, AUTH_STEP_2)

                # Read configuration
                _LOGGER.debug("Reading configuration...")
                await self.get_configuration()

                # Read alarms
                _LOGGER.debug("Reading alarms...")
                try:
                    await self.get_alarms()
                except Exception as e:
                    # Alarm sync is best-effort during bootstrap; keep connection usable.
                    _LOGGER.debug("Skipping alarm preload for %s: %s", self.mac, e)
            except Exception as e:
                _LOGGER.debug("Failed to initialize %s after connection: %s", self.mac, e)
                await self.disconnect()
                return False

            self.eventbus.send(DEVICE_CONNECT, self)

            return True

    async def connect_if_needed(self) -> bool:
        if not self.configuration or self.configuration.is_expired:
            return await self.connect()

        return False

    async def disconnect(self) -> bool:
        if self.client and self.client.is_connected:
            _LOGGER.debug(f"Disconnecting from {self.mac}...")
            if self._notify_started:
                try:
                    await self.client.stop_notify(CFG_READ_CHAR)
                except Exception:
                    _LOGGER.debug("Failed to stop notifications for %s", self.mac)
                finally:
                    self._notify_started = False
            await self.client.disconnect()
            return True

        return False

    async def delayed_disconnect(self):
        if not self.client or not self.client.is_connected:
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
            self._configuration_event.clear()
            await self._write_config(b"\x01\x02")
            await asyncio.wait_for(self._configuration_event.wait(), timeout=CONNECTION_TIMEOUT)
        else:
            raise NotConnectedError("Not connected")

    async def set_configuration(self, configuration: Configuration):
        await self._write_config(configuration.to_bytes())
        await self._write_config(b"\x01\x02")

    async def set_time(self, timestamp: int, timezone_offset: int | None = None):
        start_time = time.time()

        await self._ensure_connected()
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
            self._alarm_map = {}
            self._alarms_event.clear()
            await self._write_config(b"\x01\x06")
            await asyncio.wait_for(self._alarms_event.wait(), timeout=CONNECTION_TIMEOUT)
        else:
            raise NotConnectedError("Not connected")

    async def set_alarm(
        self,
        slot: int,
        is_enabled: bool | None,
        time: dtime | None,
        days: set[AlarmDay] | None,
        snooze: bool | None
    ) -> bool:
        await self._ensure_alarms()
        await self._ensure_connected()

        if slot >= 0 and slot < ALARM_SLOTS_COUNT:
            alarm: Alarm = self.alarms[slot]
            if is_enabled is not None:
                alarm.is_enabled = is_enabled
            if time is not None:
                alarm.time = time
            if days is not None:
                alarm.days = days
            if snooze is not None:
                alarm.snooze = snooze
            if not alarm.is_configured:
                raise ServiceValidationError("Alarm not configured.")

            await self._write_config(alarm.to_bytes())
            await self.get_alarms()
            return True

        return False

    async def delete_alarm(self, slot: int) -> bool:
        await self._ensure_alarms()
        await self._ensure_connected()

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
        async def wait_for_connected():
            while not self.client or not self.client.is_connected:
                success = await self.connect()
                if success:
                    _LOGGER.info("Successfully connected to the Bluetooth device.")
                    return
                else:
                    _LOGGER.error("Failed to connect. Retrying in %s seconds...", RETRY_INTERVAL)
                    await asyncio.sleep(RETRY_INTERVAL)

        try:
            await asyncio.wait_for(wait_for_connected(), CONNECTION_TIMEOUT)
        except asyncio.TimeoutError:
            _LOGGER.error("Connection timeout.")
            raise NotConnectedError("Connection timeout")

    async def _ensure_configuration(self):
        if not self.configuration or self.configuration.is_expired:
            await self._ensure_connected()
            await self.get_configuration()

    async def _ensure_alarms(self):
        if not self.alarms:
            await self._ensure_connected()
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

    async def _ensure_required_characteristics(self):
        if not self.client or not self.client.is_connected:
            raise NotConnectedError("Not connected")

        services = self.client.services
        if not services:
            services = await self.client.get_services()

        missing_chars = []
        for characteristic_uuid in REQUIRED_CHARS:
            if not services.get_characteristic(characteristic_uuid):
                missing_chars.append(characteristic_uuid)

        if missing_chars:
            raise NotConnectedError(
                f"Device {self.mac} is missing required characteristics: {', '.join(missing_chars)}"
            )

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
        sender_uuid = getattr(sender, "uuid", "")
        if sender_uuid.lower() == CFG_READ_CHAR.lower():
            _LOGGER.debug(f"<< {sender.uuid}: {data.hex()}")
            if data.startswith(b"\x13\x02"):
                if len(data) < 15:
                    _LOGGER.debug("Ignoring malformed config payload from %s: %s", self.mac, data.hex())
                    return
                _LOGGER.debug(f"Got configuration bytes: {data.hex()}")
                self.configuration = Configuration(data)

                self._configuration_event.set()
                self.eventbus.send(DEVICE_CONFIG_UPDATE, self.configuration)
            elif data.startswith(b"\x11\x06") and len(data) == 18:
                _LOGGER.debug(f"Got alarms bytes: {data.hex()}")
                slot_offset = data[2]
                if slot_offset == 0:
                    self._alarm_map = {}

                alarm_chunks = (
                    (slot_offset, data[3:8]),
                    (slot_offset + 1, data[8:13]),
                    (slot_offset + 2, data[13:18]),
                )
                for slot, alarm_data in alarm_chunks:
                    if 0 <= slot < ALARM_SLOTS_COUNT:
                        self._alarm_map[slot] = Alarm(slot, alarm_data)

                expected_slots = set(range(ALARM_SLOTS_COUNT))
                has_full_set = expected_slots.issubset(self._alarm_map.keys())
                has_terminal_empty_chunk = all(alarm_data == EMPTY_ALARM_BYTES for _, alarm_data in alarm_chunks)

                if has_full_set or has_terminal_empty_chunk:
                    self._finalize_alarms_from_map()
            elif data.startswith(b"\x11\x06"):
                _LOGGER.debug("Ignoring malformed alarms payload from %s: %s", self.mac, data.hex())

    def _on_disconnect(self, client: BleakClient):
        if self._disconnect_task is not None:
            self._disconnect_task.cancel()
            self._disconnect_task = None

        self._notify_started = False
        self.client = None
        self.eventbus.send(DEVICE_DISCONNECT, self)
