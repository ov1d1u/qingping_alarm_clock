import logging
from enum import Enum
from datetime import time as dtime

_LOGGER = logging.getLogger(__name__)


class AlarmDay(Enum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


class Alarm:
    is_enabled: bool | None = None
    hour: int | None = None
    minute: int | None = None
    days: set[AlarmDay] | None = None

    def __init__(self, slot: int, alarm_bytes: bytes):
        self.slot = slot

        if alarm_bytes == bytes.fromhex("ffffffffff"):
            return

        self.is_enabled = alarm_bytes[0] == 1
        self.hour = alarm_bytes[1]
        self.minute = alarm_bytes[2]
        self.days = self._bitmask_to_days(alarm_bytes[3])

        _LOGGER.debug(f"Alarm #{self.slot} enabled: {self.is_enabled}, hour: {self.hour}, minute: {self.minute}, days: {self.days}")

    @property
    def is_configured(self):
        return self.is_enabled is not None and \
            self.hour is not None and \
            self.minute is not None and \
            self.days is not None

    @property
    def time(self):
        if self.hour and self.minute:
            return dtime(self.hour, self.minute)

    @time.setter
    def time(self, value):
        self.hour = value.hour
        self.minute = value.minute

    @property
    def days_string(self):
        abbreviation_map = {
            AlarmDay.MONDAY: "mon",
            AlarmDay.TUESDAY: "tue",
            AlarmDay.WEDNESDAY: "wed",
            AlarmDay.THURSDAY: "thu",
            AlarmDay.FRIDAY: "fri",
            AlarmDay.SATURDAY: "sat",
            AlarmDay.SUNDAY: "sun",
        }
        abbreviations = [abbreviation_map[day] for day in self.days if day in abbreviation_map]
        return ",".join(abbreviations)

    def to_bytes(self) -> bytes:
        byte_array = [0x07, 0x05]
        byte_array.append(self.slot)

        if self.is_configured:
            byte_array.append(0x01 if self.is_enabled else 0x00)
            byte_array.append(self.hour)
            byte_array.append(self.minute)
            byte_array.append(self._days_to_bitmask(self.days))
            byte_array.append(0x00)
        else:
            byte_array.extend([0xff, 0xff, 0xff, 0xff, 0xff])

        return bytes(byte_array)

    def deactivate(self):
        self.is_enabled = None
        self.hour = None
        self.minute = None
        self.days = None

    def _bitmask_to_days(self, bitmask: int):
        bit_to_day = {
            1 << 0: AlarmDay.MONDAY,
            1 << 1: AlarmDay.TUESDAY,
            1 << 2: AlarmDay.WEDNESDAY,
            1 << 3: AlarmDay.THURSDAY,
            1 << 4: AlarmDay.FRIDAY,
            1 << 5: AlarmDay.SATURDAY,
            1 << 6: AlarmDay.SUNDAY
        }

        days: list[AlarmDay] = []
        for bit, day in bit_to_day.items():
            if bitmask & bit:
                days.append(day)

        return days

    def _days_to_bitmask(self, days: set[AlarmDay]):
        day_to_bit = {
            AlarmDay.MONDAY: 1 << 0,
            AlarmDay.TUESDAY: 1 << 1,
            AlarmDay.WEDNESDAY: 1 << 2,
            AlarmDay.THURSDAY: 1 << 3,
            AlarmDay.FRIDAY: 1 << 4,
            AlarmDay.SATURDAY: 1 << 5,
            AlarmDay.SUNDAY: 1 << 6
        }

        bitmask = 0
        for day in days:
            bitmask |= day_to_bit[day]

        return bitmask
