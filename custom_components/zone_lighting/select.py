"""Select platform for zone lighting"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal, Mapping

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.helpers.restore_state import RestoreEntity
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
)
from .util import initialize_with_config, ListType, get_conf_list, get_coordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    _LOGGER.info("Setting up select")
    coordinator = get_coordinator(hass, config_entry)

    scene_select = ZoneLightingSelect(
        coordinator=coordinator,
        unique_id=f"{config_entry.entry_id}_scene",
        name=f"{coordinator.zone_name} Scene",
        icon="mdi:image",
        type=MODEL_SCENE
    )
    controller_select = ZoneLightingSelect(
        coordinator=coordinator,
        unique_id=f"{config_entry.entry_id}_controller",
        name=f"{coordinator.zone_name} Controller",
        icon="mdi:remote",
        type=MODEL_CONTROLLER
    )

    async_add_entities(
        [scene_select, controller_select],
        update_before_add=True
    )

class ZoneLightingSelect(ZoneLightingEntity, SelectEntity, RestoreEntity):
    """Select for a zone lighting list"""

    coordinator: ZoneLightingCoordinator

    def __init__(
        self,
        coordinator: ZoneLightingCoordinator,
        unique_id: str,
        name: str,
        icon: str,
        type: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_name = f"Zone Lighting: {name}"
        self._attr_icon = icon
        self._list_type = type
        self._attr_options = []
        self._attr_current_option = None
        self._attr_previous_option = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None:
            self.async_schedule_update_ha_state()
            return

        self.coordinator.async_set_current_list_val(self._list_type, last_state.state)
        if ATTR_PREVIOUS_STATE in last_state.attributes:
            previous = last_state.attributes[ATTR_PREVIOUS_STATE]
            if previous in self._attr_options:
                self.coordinator.async_set_previous_list_val(self._list_type, previous)

    def _update_from_coordinator(self):
        list_data = self.coordinator.data[self._list_type]
        self._attr_options = list_data['values']
        self._attr_current_option = list_data['current']
        self._attr_previous_option = list_data['previous']

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_from_coordinator()
        self.schedule_update_ha_state()

    async def async_select_option(self, option: str) -> None:
        self.coordinator.async_set_current_list_val(self._list_type, option)

    async def async_rollback_option(self) -> None:
        self.coordinator.async_rollback_list_val(self._list_type)

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        return self._attr_current_option

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return entity specific state attributes.

        Implemented by platform classes. Convention for attribute names
        is lowercase snake_case.
        """
        return {
            ATTR_PREVIOUS_STATE: self._attr_previous_option,
        }
