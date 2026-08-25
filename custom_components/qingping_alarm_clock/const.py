"""Constants for the Qingping CGD1 Alarm Clock integration."""
DOMAIN = "qingping_alarm_clock"

ALARM_SLOTS_COUNT = 19
CONF_ALARM_SLOT = "slot"
CONF_ALARM_TIME = "time"
CONF_ALARM_DAYS = "days"
CONF_ALARM_ENABLED = "enabled"
CONF_ALARM_SNOOZE = "snooze"
CONF_TIME = "time"

SERVICE_SET_ALARM = "set_alarm"
SERVICE_DELETE_ALARM = "delete_alarm"
SERVICE_GET_ALARMS = "get_alarms"
SERVICE_SET_TIME = "set_time"
SERVICE_SYNC_TIME = "sync_time"
SERVICE_REFRESH = "refresh"

DISCONNECT_DELAY = 30
CONNECTION_TIMEOUT = 120

ATTR_ONLY_ENABLED = "only_enabled"
RETRY_INTERVAL = 10
