import sys
import types
import importlib
from pathlib import Path

# Ensure custom_components imports work when running tests from repository root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _install_homeassistant_stubs():
    homeassistant = types.ModuleType("homeassistant")
    homeassistant_core = types.ModuleType("homeassistant.core")
    homeassistant_config_entries = types.ModuleType("homeassistant.config_entries")
    homeassistant_const = types.ModuleType("homeassistant.const")
    homeassistant_exceptions = types.ModuleType("homeassistant.exceptions")
    homeassistant_components = types.ModuleType("homeassistant.components")
    homeassistant_bluetooth = types.ModuleType("homeassistant.components.bluetooth")
    homeassistant_binary_sensor = types.ModuleType("homeassistant.components.binary_sensor")
    homeassistant_helpers = types.ModuleType("homeassistant.helpers")
    homeassistant_helpers_entity = types.ModuleType("homeassistant.helpers.entity")
    homeassistant_helpers_device_registry = types.ModuleType("homeassistant.helpers.device_registry")

    class HomeAssistant:  # pragma: no cover - test stub
        pass

    def callback(func):
        return func

    class ConfigEntry:  # pragma: no cover - test stub
        pass

    class BinarySensorEntity:  # pragma: no cover - test stub
        def schedule_update_ha_state(self):
            return None

    class EntityCategory:  # pragma: no cover - test stub
        DIAGNOSTIC = "diagnostic"

    class DeviceInfo(dict):
        pass

    class HomeAssistantError(Exception):
        pass

    class ServiceValidationError(HomeAssistantError):
        pass

    def async_ble_device_from_address(*args, **kwargs):
        return None

    homeassistant_core.HomeAssistant = HomeAssistant
    homeassistant_core.callback = callback
    homeassistant_config_entries.ConfigEntry = ConfigEntry
    homeassistant_const.CONF_NAME = "name"
    homeassistant_exceptions.HomeAssistantError = HomeAssistantError
    homeassistant_exceptions.ServiceValidationError = ServiceValidationError
    homeassistant_bluetooth.async_ble_device_from_address = async_ble_device_from_address
    homeassistant_binary_sensor.BinarySensorEntity = BinarySensorEntity
    homeassistant_helpers_entity.EntityCategory = EntityCategory
    homeassistant_helpers_entity.DeviceInfo = DeviceInfo
    homeassistant_helpers_device_registry.CONNECTION_BLUETOOTH = "bluetooth"

    homeassistant.components = homeassistant_components
    homeassistant.helpers = homeassistant_helpers

    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.core", homeassistant_core)
    sys.modules.setdefault("homeassistant.config_entries", homeassistant_config_entries)
    sys.modules.setdefault("homeassistant.const", homeassistant_const)
    sys.modules.setdefault("homeassistant.exceptions", homeassistant_exceptions)
    sys.modules.setdefault("homeassistant.components", homeassistant_components)
    sys.modules.setdefault("homeassistant.components.bluetooth", homeassistant_bluetooth)
    sys.modules.setdefault("homeassistant.components.binary_sensor", homeassistant_binary_sensor)
    sys.modules.setdefault("homeassistant.helpers", homeassistant_helpers)
    sys.modules.setdefault("homeassistant.helpers.entity", homeassistant_helpers_entity)
    sys.modules.setdefault("homeassistant.helpers.device_registry", homeassistant_helpers_device_registry)


def _install_namespace_package_stubs():
    custom_components_root = REPO_ROOT / "custom_components"
    integration_root = custom_components_root / "qingping_alarm_clock"
    qingping_root = integration_root / "qingping"

    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(custom_components_root)]
    integration = types.ModuleType("custom_components.qingping_alarm_clock")
    integration.__path__ = [str(integration_root)]
    qingping = types.ModuleType("custom_components.qingping_alarm_clock.qingping")
    qingping.__path__ = [str(qingping_root)]

    sys.modules.setdefault("custom_components", custom_components)
    sys.modules.setdefault("custom_components.qingping_alarm_clock", integration)
    sys.modules.setdefault("custom_components.qingping_alarm_clock.qingping", qingping)


_install_homeassistant_stubs()
_install_namespace_package_stubs()

# Mirror qingping package exports expected by integration modules.
qingping_pkg = sys.modules["custom_components.qingping_alarm_clock.qingping"]
qingping_impl = importlib.import_module("custom_components.qingping_alarm_clock.qingping.qingping")
qingping_config = importlib.import_module("custom_components.qingping_alarm_clock.qingping.configuration")
qingping_alarm = importlib.import_module("custom_components.qingping_alarm_clock.qingping.alarm")

qingping_pkg.Qingping = qingping_impl.Qingping
qingping_pkg.Configuration = qingping_config.Configuration
qingping_pkg.Alarm = qingping_alarm.Alarm
qingping_pkg.AlarmDay = qingping_alarm.AlarmDay
