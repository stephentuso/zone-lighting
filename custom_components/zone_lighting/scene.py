"""Select platform for zone lighting"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal, Mapping

from homeassistant.components.scene import Scene
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
from .coordinator import ZoneLightingCoordinator, MODEL_SCENE
from .const import (
    ATTR_PREVIOUS_STATE,
    ATTR_ENTITIES,
    DOMAIN,
    SELECT_CONTROLLER,
    SELECT_SCENE,
    SERVICE_ROLLBACK_SELECT,
)
from .util import get_coordinator, get_scene_unique_id

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

    entities = []

    for scene in coordinator.simple_scenes:
        entity = ZoneLightingScene(
            coordinator=coordinator,
            unique_id=get_scene_unique_id(config_entry.entry_id, scene),
            name=scene,
            icon="mdi:image",
        )
        entities = entities + [entity]

    async_add_entities(
        entities,
        update_before_add=True
    )

class ZoneLightingScene(ZoneLightingEntity, Scene):
    """Zone Lighting Scene"""

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
        self._attr_name = f"{coordinator.zone_name} {name}"
        self._attr_icon = icon
        self._scene = name

        self._attr_entity_registry_visible_default = False

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate scene"""
        entities = self._entity_states
        if not entities:
            return
        task = self.hass.async_add_job(self._async_call_apply)
        if task:
            await task
        self.coordinator.async_set_current_list_val(MODEL_SCENE, self._scene)

    async def _async_call_apply(self):
        await self.hass.services.async_call("scene", "apply", dict(entities=self._entity_states))

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()

        if ATTR_ENTITIES in last_state.attributes:
            self.coordinator.async_set_scene_states(self._scene, last_state.attributes[ATTR_ENTITIES])

    @property
    def _entity_states(self):
        return self.coordinator.get_scene_states(self._scene)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.schedule_update_ha_state()

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return entity specific state attributes."""
        if not self._entity_states:
            return None
        return {
            ATTR_ENTITIES: self._entity_states,
        }
