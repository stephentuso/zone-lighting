"""Sensor platform for zone lighting"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, RestoreSensor
from homeassistant.util import slugify
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.core import (
    HomeAssistant
)
from homeassistant.const import (
    CONF_NAME,
    STATE_ON,
)

from .const import (
    DOMAIN,
    SELECT_CONTROLLER,
    SELECT_SCENE,
)
from .util import initialize_with_config, ListType, get_conf_list

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="zone_lighting",
        name="Zone Lighting Sensor",
        icon="mdi:format-quote-close",
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    _LOGGER.info("Setting up sensor")
    data = hass.data[DOMAIN]
    config_data = await initialize_with_config(hass, config_entry)
    if config_data is None:
        return

    previous_scene = HistorySensor(
        name="Scene",
        unique_id=f"{config_entry.entry_id}_previous_scene",
        options=get_conf_list(config_data, ListType.SCENE)
    )
    previous_controller = HistorySensor(
        name="Controller",
        unique_id=f"{config_entry.entry_id}_previous_controller",
        options=get_conf_list(config_data, ListType.CONTROLLER)
    )

    data[config_entry.entry_id][SELECT_SCENE] = previous_scene
    data[config_entry.entry_id][SENSOR_PREVIOUS_CONTROLLER] = previous_controller

    async_add_entities(
        [previous_scene, previous_controller],
        update_before_add=True
    )

class HistorySensor(RestoreSensor):
    """Sensor to store previous value for rolling back"""

    def __init__(
        self,
        name: str,
        unique_id: str,
        options: list[str],
    ) -> None:
        self._attr_unique_id = unique_id
        self._attr_name = f"Zone Lighting: Previous {name}"
        self._attr_options = options
        self._value = options[0]
        _LOGGER.debug(self._value)

    @property
    def icon(self) -> str:
        """Icon to use in the frontend, if any."""
        return "mdi:history"

    @property
    def native_value(self) -> str:
        return self._value

    async def async_added_to_hass(self) -> None:
        last_state = await self.async_get_last_sensor_data()
        _LOGGER.debug(f"LAST: {last_state}")
        self._value = last_state.native_value
