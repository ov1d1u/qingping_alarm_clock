from homeassistant.exceptions import HomeAssistantError


class NotConnectedError(HomeAssistantError):
    pass


class NoConfigurationError(HomeAssistantError):
    pass