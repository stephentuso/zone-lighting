"""Select platform for zone lighting"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal, Mapping

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.helpers import entity_platform, service
from homeassistant.util import slugify
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.core import (
    HomeAssistant,
    callback,
)
from homeassistant.const import (
    CONF_NAME,
    STATE_ON,
)

from .entity import ZoneLightingEntity
from .coordinator import ZoneLightingCoordinator, MODEL_SCENE, MODEL_CONTROLLER
from .const import (
    ATTR_PREVIOUS_STATE,
    DOMAIN,
    SELECT_CONTROLLER,
    SELECT_SCENE,
    SERVICE_ROLLBACK_SELECT,
)
from .util import get_coordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    coordinator = get_coordinator(hass, config_entry)

    save_scene_button = SaveSceneButton(
        coordinator=coordinator,
        unique_id=f"{config_entry.entry_id}_save_scene_button",
        name=f"{coordinator.zone_name}",
        icon="mdi:content-save",
    )

    async_add_entities(
        [save_scene_button],
        update_before_add=True
    )

class SaveSceneButton(ZoneLightingEntity, ButtonEntity):
    """Button to save the current scene state"""

    coordinator: ZoneLightingCoordinator

    def __init__(
        self,
        coordinator: ZoneLightingCoordinator,
        unique_id: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_name = f"Save {name} Scene"
        self._attr_icon = icon

    async def async_press(self):
        self.coordinator.async_save_current_scene()
