"""Config flow for Neviweb130 integration."""

from __future__ import annotations

import logging
from typing import Any

import requests
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_HOMEKIT_MODE,
    CONF_IGNORE_MIWI,
    CONF_NETWORK,
    CONF_NETWORK2,
    CONF_NETWORK3,
    CONF_NOTIFY,
    CONF_STAT_INTERVAL,
    DOMAIN,
)
from .schema import (
    HOMEKIT_MODE as DEFAULT_HOMEKIT_MODE,
    IGNORE_MIWI as DEFAULT_IGNORE_MIWI,
    NOTIFY as DEFAULT_NOTIFY,
    SCAN_INTERVAL as DEFAULT_SCAN_INTERVAL,
    STAT_INTERVAL as DEFAULT_STAT_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

REQUESTS_TIMEOUT = 30
HOST = "https://neviweb.com"
LOGIN_URL = f"{HOST}/api/login"
LOCATIONS_URL = f"{HOST}/api/locations?account$id="


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]

    # Test if we can authenticate with provided credentials
    try:
        login_data = {
            "username": username,
            "password": password,
            "interface": "neviweb",
            "stayConnected": 1,
        }

        response = await hass.async_add_executor_job(
            lambda: requests.post(LOGIN_URL, json=login_data, timeout=REQUESTS_TIMEOUT)
        )

        if response.status_code != 200:
            _LOGGER.error("Login failed with status code: %s", response.status_code)
            raise InvalidAuth

        response_data = response.json()
        if "error" in response_data:
            error_code = response_data["error"]["code"]
            _LOGGER.error("Login error: %s", error_code)
            if error_code == "USRBADLOGIN":
                raise InvalidAuth
            raise CannotConnect

        # Get account ID and session
        account_id = str(response_data["account"]["id"])
        session_id = response_data["session"]
        cookies = response.cookies

        # Get available networks
        headers = {"Session-Id": session_id}
        locations_response = await hass.async_add_executor_job(
            lambda: requests.get(
                LOCATIONS_URL + account_id, headers=headers, cookies=cookies, timeout=REQUESTS_TIMEOUT
            )
        )

        networks = locations_response.json()
        network_names = [network["name"] for network in networks]

        _LOGGER.debug("Available networks: %s", network_names)

        return {
            "title": username,
            "networks": network_names,
        }

    except requests.exceptions.Timeout:
        raise CannotConnect
    except requests.exceptions.RequestException:
        raise CannotConnect


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Neviweb130."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._networks: list[str] = []
        self._username: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                self._networks = info["networks"]
                self._username = user_input[CONF_USERNAME]

                # Set unique ID based on username to prevent duplicates
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()

                # Store user input for next step
                self.context["user_input"] = user_input

                # If networks are available, proceed to network selection
                if self._networks:
                    return await self.async_step_networks()

                # If no networks, create entry directly
                return self.async_create_entry(title=info["title"], data=user_input)

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_networks(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle network selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Merge with previous user input
            data = self.context["user_input"]
            
            # Add optional network selections
            if user_input.get(CONF_NETWORK):
                data[CONF_NETWORK] = user_input[CONF_NETWORK]
            if user_input.get(CONF_NETWORK2):
                data[CONF_NETWORK2] = user_input[CONF_NETWORK2]
            if user_input.get(CONF_NETWORK3):
                data[CONF_NETWORK3] = user_input[CONF_NETWORK3]

            return await self.async_step_options(user_input=data)

        # Build network selection schema with discovered networks
        network_options = [""] + self._networks  # Empty string for "none"
        
        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NETWORK): vol.In(network_options),
                vol.Optional(CONF_NETWORK2): vol.In(network_options),
                vol.Optional(CONF_NETWORK3): vol.In(network_options),
            }
        )

        return self.async_show_form(
            step_id="networks",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "networks": ", ".join(self._networks) if self._networks else "None",
            },
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle optional configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Extract options from user_input
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            if isinstance(scan_interval, int):
                pass  # Already in seconds
            elif hasattr(scan_interval, "total_seconds"):
                scan_interval = int(scan_interval.total_seconds())
            else:
                scan_interval = int(DEFAULT_SCAN_INTERVAL.total_seconds())

            stat_interval = user_input.get(CONF_STAT_INTERVAL, DEFAULT_STAT_INTERVAL)
            
            # Build final data dictionary
            data = {
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_SCAN_INTERVAL: scan_interval,
                CONF_HOMEKIT_MODE: user_input.get(CONF_HOMEKIT_MODE, DEFAULT_HOMEKIT_MODE),
                CONF_IGNORE_MIWI: user_input.get(CONF_IGNORE_MIWI, DEFAULT_IGNORE_MIWI),
                CONF_STAT_INTERVAL: stat_interval,
                CONF_NOTIFY: user_input.get(CONF_NOTIFY, DEFAULT_NOTIFY),
            }

            # Add optional networks if provided
            if user_input.get(CONF_NETWORK):
                data[CONF_NETWORK] = user_input[CONF_NETWORK]
            if user_input.get(CONF_NETWORK2):
                data[CONF_NETWORK2] = user_input[CONF_NETWORK2]
            if user_input.get(CONF_NETWORK3):
                data[CONF_NETWORK3] = user_input[CONF_NETWORK3]

            return self.async_create_entry(title=self._username or data[CONF_USERNAME], data=data)

        # Get default scan_interval in seconds
        default_scan_seconds = int(DEFAULT_SCAN_INTERVAL.total_seconds())

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=default_scan_seconds
                ): vol.All(vol.Coerce(int), vol.Range(min=300, max=600)),
                vol.Optional(
                    CONF_HOMEKIT_MODE, default=DEFAULT_HOMEKIT_MODE
                ): cv.boolean,
                vol.Optional(
                    CONF_IGNORE_MIWI, default=DEFAULT_IGNORE_MIWI
                ): cv.boolean,
                vol.Optional(
                    CONF_STAT_INTERVAL, default=DEFAULT_STAT_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=300, max=1800)),
                vol.Optional(CONF_NOTIFY, default=DEFAULT_NOTIFY): vol.In(
                    ["both", "logging", "nothing", "notification"]
                ),
            }
        )

        return self.async_show_form(
            step_id="options", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Neviweb130."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Update config entry with new options
            return self.async_create_entry(title="", data=user_input)

        # Get current values from options first, then fall back to data
        current_data = {**self.config_entry.data, **self.config_entry.options}
        
        current_scan_interval = current_data.get(
            CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds())
        )
        current_stat_interval = current_data.get(
            CONF_STAT_INTERVAL, DEFAULT_STAT_INTERVAL
        )
        current_homekit_mode = current_data.get(
            CONF_HOMEKIT_MODE, DEFAULT_HOMEKIT_MODE
        )
        current_ignore_miwi = current_data.get(
            CONF_IGNORE_MIWI, DEFAULT_IGNORE_MIWI
        )
        current_notify = current_data.get(CONF_NOTIFY, DEFAULT_NOTIFY)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=current_scan_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=300, max=600)),
                vol.Optional(
                    CONF_HOMEKIT_MODE, default=current_homekit_mode
                ): cv.boolean,
                vol.Optional(
                    CONF_IGNORE_MIWI, default=current_ignore_miwi
                ): cv.boolean,
                vol.Optional(
                    CONF_STAT_INTERVAL, default=current_stat_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=300, max=1800)),
                vol.Optional(CONF_NOTIFY, default=current_notify): vol.In(
                    ["both", "logging", "nothing", "notification"]
                ),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
