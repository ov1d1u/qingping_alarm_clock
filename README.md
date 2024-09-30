# Qingping Cleargrass CGD1 Clock Home Assistant Integration

This custom integration allows you to control and configure the Qingping Cleargrass CGD1 clock directly from Home Assistant. You can set alarms, adjust settings, and keep the time synchronized with your Home Assistant instance.

## Features

- **Set Alarms**: Configure alarms with specific times, days, and enable/disable them.
- **Delete Alarms**: Remove configured alarms.
- **Set Time**: Set the clock's time and timezone.
- **Refresh Data**: Manually refresh data from the clock.
- **Adjust Settings**: Modify the clock settings such as language, time format, temperature unit, sound volume, screen light duration, and brightness levels.

## Services

### `set_alarm`
Set an alarm with specified parameters.

```yaml
service: qingping_alarm_clock.set_alarm
data:
  device_id: "your_device_id"
  slot: 1
  time: "07:30"
  days: "mon,wed,fri"
  enabled: true
```

### `delete_alarm`
Delete a specified alarm.

```yaml
service: qingping_alarm_clock.delete_alarm
data:
  device_id: "your_device_id"
  slot: 1
```

### `set_time`
Set the device time.

```yaml
service: qingping_alarm_clock.set_time
data:
  device_id: "your_device_id"
  time: "2022-02-22 13:30:00"
  timezone: "Europe/Bucharest"
```

### `refresh`
Refresh the clock data.

```yaml
service: qingping_alarm_clock.refresh
data:
  device_id: "your_device_id"
```

## Installation

### Manual Installation

1. Download the zip file of the latest version from the [releases page](https://github.com/ov1d1u/qingping_alarm_clock/releases).
2. Unzip it and copy the `qingping_alarm_clock` directory into your `custom_components` directory within your Home Assistant configuration directory.
3. Restart Home Assistant.
4. Configure the integration via the Home Assistant UI by navigating to **Configuration** > **Integrations** > **Add Integration** and searching for "Qingping Alarm Clock".

### Installation via HACS

1. Ensure you have [HACS](https://hacs.xyz) installed.
2. Add this repository to HACS: Go to **HACS** > **Integrations** > **Custom repositories** > **Add** and enter the repository URL.
3. Search for "Qingping Alarm Clock" in HACS and install it.
4. Restart Home Assistant.
5. Configure the integration via the Home Assistant UI by navigating to **Configuration** > **Integrations** > **Add Integration** and searching for "Qingping Alarm Clock".

## Device Entities

### Select Entities
- Language
- Time Format
- Temperature Unit

### Number Entities
- Sound Volume
- Screenlight Time
- Daytime Brightness
- Nighttime Brightness

### Switch Entities
- Alarms Switch

### Time Entities
- Nighttime Start
- Nighttime End

## Contributing

Feel free to open issues or create pull requests if you have any suggestions or find any bugs.

## Acknowledgements

Thanks to [@koenvervloesem](https://github.com/koenvervloesem) for his help with reverse-engineering the authentication on the Qingping Cleargrass CGD1 clock.

## Notes

This is a very alpha version. It may work well or it may not work at all for you. If you encounter any issues, please [open an issue](https://github.com/ov1d1u/qingping_alarm_clock/issues) on GitHub.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.