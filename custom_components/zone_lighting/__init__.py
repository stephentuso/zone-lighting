"""Zone Lighting integration in Home-Assistant."""

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant

from .const import (
    _DOMAIN_SCHEMA,
    CONF_NAME,
    COORDINATOR,
    DOMAIN,
    UNDO_UPDATE_LISTENER,
)
from .util import initialize_with_config
from .coordinator import ZoneLightingCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["light", "select"]

def _all_unique_names(value):
    """Validate that all entities have a unique profile name."""
    hosts = [device[CONF_NAME] for device in value]
    schema = vol.Schema(vol.Unique())
    schema(hosts)
    return value

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [_DOMAIN_SCHEMA], _all_unique_names)},
    extra=vol.ALLOW_EXTRA,
)

async def reload_configuration_yaml(event: dict, hass: HomeAssistant):  # noqa: ARG001
    """Reload configuration.yaml."""
    await hass.services.async_call("homeassistant", "check_config", {})


async def async_setup(hass: HomeAssistant, config: dict[str, Any]):
    """Import integration from config."""
    if DOMAIN in config:
        for entry in config[DOMAIN]:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={CONF_SOURCE: SOURCE_IMPORT},
                    data=entry,
                ),
            )
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the component."""
    data = hass.data.setdefault(DOMAIN, {})

    # This will reload any changes the user made to any YAML configurations.
    # Called during 'quick reload' or hass.reload_config_entry
    hass.bus.async_listen("hass.config.entry_updated", reload_configuration_yaml)

    undo_listener = config_entry.add_update_listener(async_update_options)
    data[config_entry.entry_id] = {UNDO_UPDATE_LISTENER: undo_listener}
    config_data = await initialize_with_config(hass, config_entry)
    coordinator = ZoneLightingCoordinator(hass, config_data)
    data[config_entry.entry_id][COORDINATOR] = coordinator
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform),
        )

    return True


async def async_update_options(hass, config_entry: ConfigEntry):
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_results = []
    for platform in PLATFORMS:
        result = await hass.config_entries.async_forward_entry_unload(
            config_entry,
            platform,
        )
        unload_results.append(result)

    unload_ok = all(unload_results)

    data = hass.data[DOMAIN]
    data[config_entry.entry_id][UNDO_UPDATE_LISTENER]()
    if unload_ok:
        data.pop(config_entry.entry_id)

    if not data:
        hass.data.pop(DOMAIN)

    return unload_ok
