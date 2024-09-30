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