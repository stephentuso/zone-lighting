from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal
from copy import deepcopy
from enum import Enum
import logging

from homeassistant.const import (
    ATTR_ENTITY_ID,
)
from homeassistant.core import (
    HomeAssistant
)
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_SCENES,
    CONF_SCENES_EVENT,
    CONF_CONTROLLERS,
    COORDINATOR,
    DOMAIN,
    MANUAL,
    SELECT_CONTROLLER,
    SELECT_SCENE,
    OPTIONS_LIST,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from .coordinator import ZoneLightingCoordinator

_LOGGER = logging.getLogger(__name__)

def parse_config(
    config_entry: ConfigEntry | None,
    service_data: dict[str, Any] | None = None,
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Get the options and data from the config_entry and add defaults."""
    if defaults is None:
        data = {key: default for key, default in map(lambda entry: (entry['name'], entry['default']), OPTIONS_LIST)}
    else:
        data = deepcopy(defaults)

    if config_entry is not None:
        assert service_data is None
        assert defaults is None
        data.update(config_entry.options)  # come from options flow
        data.update(config_entry.data)  # all yaml settings come from data
    else:
        assert service_data is not None
        changed_settings = {
            key: value
            for key, value in service_data.items()
            if key not in (ATTR_ENTITY_ID)
        }
        data.update(changed_settings)
    return data

async def initialize_with_config(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, Any] | None:
    """Initialize Zone Lighting config entry."""
    data = hass.data[DOMAIN]
    assert config_entry.entry_id in data
    _LOGGER.debug(
        "Setting up Zone Lighting with data: %s and config_entry %s",
        data,
        config_entry,
    )
    if (  # Skip deleted YAML config entries or first time YAML config entries
        config_entry.source == SOURCE_IMPORT
        and config_entry.unique_id not in data.get("__yaml__", set())
    ):
        _LOGGER.warning(
            "Deleting Zone Lighting switch '%s' because YAML"
            " defined switch has been removed from YAML configuration",
            config_entry.unique_id,
        )
        await hass.config_entries.async_remove(config_entry.entry_id)
        return None

    return parse_config(config_entry)

def get_coordinator(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> ZoneLightingCoordinator:
    data = hass.data[DOMAIN]
    assert config_entry.entry_id in data
    return data[config_entry.entry_id][COORDINATOR]

class ListType(Enum):
    SCENE = 0
    CONTROLLER = 1

conf_mapping = {
    ListType.CONTROLLER: [CONF_CONTROLLERS],
    ListType.SCENE: [CONF_SCENES, CONF_SCENES_EVENT],
}

select_mapping = {
    ListType.CONTROLLER: SELECT_CONTROLLER,
    ListType.SCENE: SELECT_SCENE,
}

def filter_conf_list(values: list[str]):
    return list(filter(lambda value: bool(value), values))

def get_conf_list_plain(data: dict[str, Any], key: str):
    return filter_conf_list(data[key])

def get_conf_list(data: dict[str, Any], type: ListType):
    all_items = [MANUAL]
    for param in conf_mapping[type]:
        if data[param]:
            all_items += get_conf_list_plain(data, param)
    return all_items

def validate_list_option(data: dict[str, Any], type: ListType, option: str):
    return option in get_conf_list(data, type)

def get_select_for_list(hass: HomeAssistant, entry_id: str, type: ListType):
    return hass.data[DOMAIN][entry_id][select_mapping[type]]

def get_current_list_option(hass: HomeAssistant, entry_id: str, type: ListType):
    return get_select_for_list(hass, entry_id, type).current_option

def get_scene_unique_id(entry_id: str, scene: str):
    return f"{entry_id}_scene_{scene}"

def async_get_scene_entity_id(hass: HomeAssistant, entry_id: str, scene: str):
    registry = er.async_get(hass)
    return registry.async_get_entity_id("scene", DOMAIN, get_scene_unique_id(entry_id, scene))
