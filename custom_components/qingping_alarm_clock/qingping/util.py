from functools import wraps

from .alarm import AlarmDay


def alarm_days_from_string(days_string: str):
    abbreviation_map = {
        "mon": AlarmDay.MONDAY,
        "tue": AlarmDay.TUESDAY,
        "wed": AlarmDay.WEDNESDAY,
        "thu": AlarmDay.THURSDAY,
        "fri": AlarmDay.FRIDAY,
        "sat": AlarmDay.SATURDAY,
        "sun": AlarmDay.SUNDAY,
    }

    abbreviations = days_string.split(',')
    alarm_days = [abbreviation_map[abbr] for abbr in abbreviations if abbr in abbreviation_map]
    return alarm_days


def updates_configuration(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        await self._ensure_configuration()
        return_value = await func(self, *args, **kwargs)
        await self._get_configuration()
        return return_value
    return wrapper


def ensure_alarms(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        await self._ensure_alarms()
        return await func(self, *args, **kwargs)
    return wrapper
