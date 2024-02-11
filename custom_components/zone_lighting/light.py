"""Light platform for Zone Lighting"""
from __future__ import annotations

from collections import Counter
import itertools
import logging
import re
from typing import Any, cast

import voluptuous as vol

from homeassistant.components.group.light import LightGroup
from homeassistant.util import slugify
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.components import light
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_FLASH,
    ATTR_HS_COLOR,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_RGBWW_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_TRANSITION,
    ATTR_WHITE,
    ATTR_XY_COLOR,
    PLATFORM_SCHEMA,
    ColorMode,
    LightEntity,
    LightEntityFeature,
    filter_supported_color_modes,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    CONF_ENTITIES,
    CONF_NAME,
    CONF_UNIQUE_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    DOMAIN,
    CONF_LIGHTS,
    CONF_SCENES,
    MANUAL,
)
from .util import (
    initialize_with_config,
    get_coordinator,
)
from .entity import ZoneLightingEntity
from .coordinator import ZoneLightingCoordinator, MODEL_SCENE, MODEL_CONTROLLER, MODEL_STATE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config_data = await initialize_with_config(hass, config_entry)
    coordinator = get_coordinator(hass, config_entry)

    async_add_entities(
        [LightZone(
            coordinator,
            config_entry.entry_id,
        )],
        update_before_add=True
    )

FORWARDED_ATTRIBUTES = frozenset(
    {
        ATTR_BRIGHTNESS,
        ATTR_COLOR_TEMP_KELVIN,
        ATTR_FLASH,
        ATTR_HS_COLOR,
        ATTR_RGB_COLOR,
        ATTR_RGBW_COLOR,
        ATTR_RGBWW_COLOR,
        ATTR_TRANSITION,
        ATTR_WHITE,
        ATTR_XY_COLOR,
    }
)

SCENE_PREFIX = "Scene"
CONTROL_PREFIX = "Control"

def add_prefix(prefix: str):
    return lambda val: f"{prefix}: {val}"

def show_selected(current_val: str):
    return lambda val: f"{val} ✅" if val == current_val else val

class LightZone(ZoneLightingEntity, LightGroup, RestoreEntity):
    """Representation of a light zone"""

    coordinator: ZoneLightingCoordinator

    def __init__(
        self,
        coordinator: ZoneLightingCoordinator,
        unique_id: str,
    ) -> None:
        ZoneLightingEntity.__init__(self, coordinator)
        LightGroup.__init__(self, unique_id, coordinator.zone_name, coordinator.light_entity_ids, None)

    @property
    def is_manual(self):
        if not self.coordinator.data:
            return False
        return self.coordinator.data[MODEL_SCENE]['current'] == MANUAL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        _LOGGER.debug("%s: last state is %s", self.name, last_state)
        if (last_state is not None and last_state.state == STATE_ON):
            self.coordinator.async_set_on_state(True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.async_set_on_state(True)

        effect = None
        effect_type = None
        if ATTR_EFFECT in kwargs:
            pattern = r"^(.*?): "
            type_match = re.match(pattern, kwargs[ATTR_EFFECT])
            if type_match:
                effect = re.sub(pattern, "", kwargs[ATTR_EFFECT])
                if type_match.group(1) == SCENE_PREFIX:
                    effect_type = MODEL_SCENE
                elif type_match.group(1) == CONTROL_PREFIX:
                    effect_type = MODEL_CONTROLLER

        if effect_type and effect:
            self.coordinator.async_set_current_list_val(effect_type, effect)

        if self.is_manual or (effect_type == SCENE_PREFIX and effect == MANUAL):
            await self.async_proxy_turn_on(**kwargs)
            return

    async def async_proxy_turn_on(self, **kwargs: Any) -> None:
        """Forward the turn_on command to all lights in the light group if all off, or only currently the currently on lights."""
        data = {
            key: value for key, value in kwargs.items() if key in FORWARDED_ATTRIBUTES
        }
        if self.state == STATE_ON:
            on_ids = [
                entity_id
                for entity_id in self._entity_ids
                if (state := self.hass.states.get(entity_id)) is not None and state.state == STATE_ON
            ]
            data[ATTR_ENTITY_ID] = on_ids
            pass
        else:
            data[ATTR_ENTITY_ID] = self._entity_ids

        _LOGGER.debug("Forwarded turn_on command: %s", data)

        await self.hass.services.async_call(
            light.DOMAIN,
            SERVICE_TURN_ON,
            data,
            blocking=True,
            context=self._context,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.async_set_on_state(False)
        await LightGroup.async_turn_off(self, **kwargs)
        # if self.is_manual:
            # return

        # self.async_update_group_state()
        # self.async_schedule_update_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_update_group_state()
        self.schedule_update_ha_state()

    @callback
    def async_update_group_state(self) -> None:
        LightGroup.async_update_group_state(self)
        self._attr_supported_features |= LightEntityFeature.EFFECT

        if not self.coordinator.data:
            return

        scene_model = self.coordinator.data[MODEL_SCENE]
        scenes = list(map(add_prefix(SCENE_PREFIX), map(show_selected(scene_model["current"]), scene_model["values"])))

        controller_model = self.coordinator.data[MODEL_CONTROLLER]
        controllers = list(map(add_prefix(CONTROL_PREFIX), map(show_selected(controller_model["current"]), controller_model["values"])))

        self._attr_effect_list = scenes + controllers
        self._attr_effect = None

        if self.is_manual:
            if self.coordinator.data[MODEL_STATE] != self._attr_is_on:
                self.coordinator.async_set_on_state(self._attr_is_on)
            return

        self._attr_is_on = self.coordinator.data[MODEL_STATE]
        self._attr_supported_color_modes = {ColorMode.ONOFF}

        self.coordinator.async_save_current_scene()

