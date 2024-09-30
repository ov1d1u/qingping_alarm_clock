import voluptuous as vol

def is_time(value):
    """Validate time in HH:MM format."""
    try:
        parts = value.split(':')
        if len(parts) != 2:
            raise vol.Invalid("Time must be in HH:MM format.")
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise vol.Invalid("Hour must be 0-23 and minute must be 0-59.")
        return value
    except Exception:
        raise vol.Invalid("Time must be in HH:MM format.")

def is_days(value):
    """Validate days as a comma-separated list of valid weekdays."""
    valid_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    days = value.split(',')
    for day in days:
        if day.lower() not in valid_days:
            raise vol.Invalid(f"Invalid day: {day}. Must be one of: {', '.join(valid_days)}")
    return value