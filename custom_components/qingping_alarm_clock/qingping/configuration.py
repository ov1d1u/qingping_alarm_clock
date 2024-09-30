from datetime import time, datetime, timedelta
from enum import Enum

CONFIGURATION_VALIDITY_TIME = timedelta(minutes=30)


class Language(Enum):
    EN = "en"
    ZH = "zh"


class Configuration:
    def __init__(self, config_bytes):
        self.date = datetime.now()

        self._sound_volume = config_bytes[2]
        self._timezone_offset = config_bytes[6] * 6
        self._screen_light_time = config_bytes[7]

        brightness = self._byte_to_brightness(config_bytes[8])
        self._daytime_brightness, self._nighttime_brightness = brightness
        self._night_time_start_hour = config_bytes[9]
        self._night_time_start_minute = config_bytes[10]
        self._night_time_end_hour = config_bytes[11]
        self._night_time_end_minute = config_bytes[12]
        self._tz_plus_flag = config_bytes[13] == 1

        self._language = Language.ZH if config_bytes[5] & 1 << 0 == 0 else Language.EN
        self._use_24h_format = config_bytes[5] & 1 << 1 == 0
        self._use_celsius = config_bytes[5] & 1 << 2 == 0
        self._alarms_on = config_bytes[5] & 1 << 4 == 0

    @property
    def is_expired(self):
        return self.date + CONFIGURATION_VALIDITY_TIME < datetime.now()

    @property
    def sound_volume(self):
        return self._sound_volume

    @sound_volume.setter
    def sound_volume(self, value):
        if value < 1 or value > 5:
            return ValueError
        self._sound_volume = value

    @property
    def timezone_offset(self):
        """ Timezone offset in minutes. """
        if self._tz_plus_flag:
            return self._timezone_offset
        else:
            return -self._timezone_offset

    @timezone_offset.setter
    def timezone_offset(self, value):
        if value > 720 or value < -720:
            return ValueError
        self._timezone_offset = abs(value)
        self._tz_plus_flag = value >= 0

    @property
    def screen_light_time(self):
        return self._screen_light_time

    @screen_light_time.setter
    def screen_light_time(self, value):
        if value < 1 or value > 30:
            return ValueError
        self._screen_light_time = value

    @property
    def daytime_brightness(self):
        return self._daytime_brightness

    @daytime_brightness.setter
    def daytime_brightness(self, value):
        if value < 1 or value > 100:
            return ValueError
        self._daytime_brightness = value

    @property
    def nighttime_brightness(self):
        return self._nighttime_brightness

    @nighttime_brightness.setter
    def nighttime_brightness(self, value):
        if value < 1 or value > 100:
            return ValueError
        self._nighttime_brightness = value

    @property
    def night_time_start_hour(self):
        return self._night_time_start_hour

    @night_time_start_hour.setter
    def night_time_start_hour(self, value):
        if value < 0 or value > 23:
            return ValueError
        self._night_time_start_hour = value

    @property
    def night_time_start_minute(self):
        return self._night_time_start_minute

    @night_time_start_minute.setter
    def night_time_start_minute(self, value):
        if value < 0 or value > 59:
            return ValueError
        self._night_time_start_minute = value

    @property
    def night_time_end_hour(self):
        return self._night_time_end_hour

    @night_time_end_hour.setter
    def night_time_end_hour(self, value):
        if value < 0 or value > 23:
            return ValueError
        self._night_time_end_hour = value

    @property
    def night_time_end_minute(self):
        return self._night_time_end_minute

    @night_time_end_minute.setter
    def night_time_end_minute(self, value):
        if value < 0 or value > 59:
            return ValueError
        self._night_time_end_minute = value

    @property
    def night_time_start_time(self):
        return time(hour=self._night_time_start_hour, minute=self._night_time_start_minute)

    @night_time_start_time.setter
    def night_time_start_time(self, value: time):
        self._night_time_start_hour = value.hour
        self._night_time_start_minute = value.minute

    @property
    def night_time_end_time(self):
        return time(hour=self._night_time_end_hour, minute=self._night_time_end_minute)

    @night_time_end_time.setter
    def night_time_end_time(self, value: time):
        self._night_time_end_hour = value.hour
        self._night_time_end_minute = value.minute

    @property
    def language(self):
        return self._language

    @language.setter
    def language(self, value):
        self._language = value

    @property
    def use_24h_format(self):
        return self._use_24h_format

    @use_24h_format.setter
    def use_24h_format(self, value):
        self._use_24h_format = value

    @property
    def use_celsius(self):
        return self._use_celsius

    @use_celsius.setter
    def use_celsius(self, value):
        self._use_celsius = value

    @property
    def alarms_on(self):
        return self._alarms_on

    @alarms_on.setter
    def alarms_on(self, value):
        self._alarms_on = value

    def to_bytes(self):
        byte_array = [0x13, 0x01]
        byte_array.append(self.sound_volume)
        byte_array.extend([0xff, 0xff])

        config_byte = 0
        config_byte |= 0 if self.language == Language.ZH else (1 << 0)
        config_byte |= 0 if self.use_24h_format else (1 << 1)
        config_byte |= 0 if self.use_celsius else (1 << 2)
        config_byte |= 0 if self.alarms_on else (1 << 4)
        byte_array.append(config_byte)

        byte_array.append(self.timezone_offset // 6)
        byte_array.append(self.screen_light_time)
        byte_array.append(
            self._brightness_to_byte(self.daytime_brightness, self.nighttime_brightness)
        )

        byte_array.append(self.night_time_start_hour)
        byte_array.append(self.night_time_start_minute)

        byte_array.append(self.night_time_end_hour)
        byte_array.append(self.night_time_end_minute)
        byte_array.append(b'\x01' if self._tz_plus_flag else b'\x00')

        byte_array.append(b'\xff' * 6)
        bytes_result = b''.join([bytes([x]) if isinstance(x, int) else x for x in byte_array])

        if len(bytes_result) != 20:
            raise ValueError("Configuration bytes must be 20 bytes long.")

        return bytes_result

    def _byte_to_brightness(self, int_value):
        first_nibble = (int_value >> 4) & 0x0F
        second_nibble = int_value & 0x0F

        daytime_brightness = first_nibble * 10
        nighttime_brightness = second_nibble * 10

        return (daytime_brightness, nighttime_brightness)

    def _brightness_to_byte(self, daytime_brightness, nighttime_brightness):
        if not 0 <= daytime_brightness <= 100 or daytime_brightness % 10 != 0:
            raise ValueError("Daytime brightness must be between 0 and 100 and a multiple of 10.")
        if not 0 <= nighttime_brightness <= 100 or nighttime_brightness % 10 != 0:
            raise ValueError("Nighttime brightness must be between 0 and 100 and a multiple of 10.")

        first_nibble = daytime_brightness // 10
        second_nibble = nighttime_brightness // 10

        combined_byte_value = (first_nibble << 4) | second_nibble
        combined_byte = combined_byte_value.to_bytes(1, byteorder='big')

        return combined_byte