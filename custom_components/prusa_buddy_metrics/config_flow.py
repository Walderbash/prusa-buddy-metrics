import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_UDP_PORT,
    DEFAULT_UDP_PORT,
)


class PrusaBuddyMetricsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Prusa Buddy Metrics."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            port = user_input[CONF_UDP_PORT]
            if not (1 <= port <= 65535):
                errors[CONF_UDP_PORT] = "invalid_port"
            else:
                await self.async_set_unique_id(f"prusa_buddy_{port}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Prusa Buddy Metrics (port {port})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_UDP_PORT, default=DEFAULT_UDP_PORT): int,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PrusaBuddyMetricsOptionsFlow(config_entry)


class PrusaBuddyMetricsOptionsFlow(config_entries.OptionsFlow):
    """Handle options (allows changing port/name after setup)."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}

        if user_input is not None:
            port = user_input[CONF_UDP_PORT]
            if not (1 <= port <= 65535):
                errors[CONF_UDP_PORT] = "invalid_port"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UDP_PORT,
                        default=self.config_entry.data.get(
                            CONF_UDP_PORT, DEFAULT_UDP_PORT
                        ),
                    ): int,
                }
            ),
            errors=errors,
        )
