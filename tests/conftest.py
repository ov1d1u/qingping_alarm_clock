import sys
import types
from pathlib import Path

# Ensure custom_components imports work when running tests from repository root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _install_homeassistant_stubs():
    homeassistant = types.ModuleType("homeassistant")
    homeassistant_core = types.ModuleType("homeassistant.core")
    homeassistant_exceptions = types.ModuleType("homeassistant.exceptions")
    homeassistant_components = types.ModuleType("homeassistant.components")
    homeassistant_bluetooth = types.ModuleType("homeassistant.components.bluetooth")

    class HomeAssistant:  # pragma: no cover - test stub
        pass

    class HomeAssistantError(Exception):
        pass

    class ServiceValidationError(HomeAssistantError):
        pass

    def async_ble_device_from_address(*args, **kwargs):
        return None

    homeassistant_core.HomeAssistant = HomeAssistant
    homeassistant_exceptions.HomeAssistantError = HomeAssistantError
    homeassistant_exceptions.ServiceValidationError = ServiceValidationError
    homeassistant_bluetooth.async_ble_device_from_address = async_ble_device_from_address

    homeassistant.components = homeassistant_components

    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.core", homeassistant_core)
    sys.modules.setdefault("homeassistant.exceptions", homeassistant_exceptions)
    sys.modules.setdefault("homeassistant.components", homeassistant_components)
    sys.modules.setdefault("homeassistant.components.bluetooth", homeassistant_bluetooth)


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
