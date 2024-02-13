"""DataUpdateCoordinator for Zone Lighting."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.debounce import Debouncer
from homeassistant.util import slugify
from homeassistant.const import (
    CONF_DEVICE_ID,
)

from .const import (
    CONF_NAME,
    CONF_LIGHTS,
    CONF_SCENES,
    CONF_SCENES_EVENT,
    DOMAIN,
    CONF_EVENT_SCENE,
    CONF_EVENT_ACTION,
    ACTION_ACTIVATE,
    ACTION_DEACTIVATE,
    ZONE_LIGHTING_EVENT,
)
from .util import (
    ListType,
    MANUAL,
    get_conf_list,
)

_LOGGER = logging.getLogger(__name__)

MODEL_SCENE = "scene"
MODEL_CONTROLLER = "controller"
MODEL_STATE = "on_state"

class ZoneLightingCoordinator(DataUpdateCoordinator):
    """Class to manage data"""

    config_entry: ConfigEntry
    zone_name: str

    _model: dict[str, Any]
    _device_id = None
    _light_entity_ids = None

    def __init__(
        self,
        hass: HomeAssistant,
        config_data: dict[str, Any],
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=DOMAIN,
            always_update=False,
        )
        self.config_data = config_data
        self.device_identifiers = {(DOMAIN, self.config_entry.entry_id)}
        self.zone_name = self.config_data[CONF_NAME]

        self._simple_scenes = self.config_data[CONF_SCENES]
        self._event_scenes = self.config_data[CONF_SCENES_EVENT]

        self._scene_restored = False

        scenes = get_conf_list(self.config_data, ListType.SCENE)
        controllers = get_conf_list(self.config_data, ListType.CONTROLLER)
        self._model = {
            MODEL_STATE: False,
            MODEL_SCENE: dict(values=scenes, current=None, previous=None),
            MODEL_CONTROLLER: dict(values=controllers, current=None, previous=None),
        }

        self._save_current_scene_debouncer = Debouncer(
            hass,
            _LOGGER,
            cooldown=5,
            immediate=False,
            function=self._async_save_current_scene,
        )

    @property
    def light_entity_ids(self):
        if not self._light_entity_ids:
            registry = entity_registry.async_get(self.hass)
            self._light_entity_ids = entity_registry.async_validate_entity_ids(registry, self.config_data[CONF_LIGHTS])
        return self._light_entity_ids

    @property
    def device_id(self):
        if not self._device_id:
            entry = device_registry.async_get(self.hass).async_get_device(self.device_identifiers)
            if entry:
                self._device_id = entry.id
        return self._device_id

    def _async_data_changed(self):
        self.async_set_updated_data(self._model)

    async def _async_update_data(self):
        return self._model

    def _is_simple_scene(self, scene: str):
        if not scene or scene == MANUAL:
            return False

        return scene in self._simple_scenes

    def _async_handle_scene_action(self, action: str, scene: str):
        if not scene or scene == MANUAL:
            return

        if scene in self._event_scenes:
            self._async_fire_scene_event(action, scene)
            return

        if action == ACTION_ACTIVATE:
            self.hass.add_job(self._async_restore_scene_state, scene)
        elif action == ACTION_DEACTIVATE:
            self.hass.add_job(self._async_save_scene_state, scene)

    def _async_fire_scene_event(self, action: str, scene: str):
        if not self.device_id:
            return
        self.hass.bus.async_fire(ZONE_LIGHTING_EVENT, {
            CONF_DEVICE_ID: self.device_id,
            CONF_EVENT_ACTION: action,
            CONF_EVENT_SCENE: scene
        })

    def _get_saved_scene_id(self, scene):
        return f"zone_lighting_{slugify(self.zone_name)}_{slugify(scene)}"

    def async_save_current_scene(self):
        if not self._model[MODEL_STATE]:
            return
        self.hass.add_job(self._save_current_scene_debouncer.async_call)

    def _async_save_current_scene(self):
        if not self._model[MODEL_STATE]:
            return

        scene = self._model[MODEL_SCENE]["current"]
        if self._is_simple_scene(scene):
            self.hass.add_job(self._async_save_scene_state, scene)
            # self._async_save_scene_state(scene)

    async def _async_save_scene_state(self, scene):
        if not self._model[MODEL_STATE]:
            return

        if not self._scene_restored:
            _LOGGER.debug("Not saving scene state, scene not restored yet")
            return

        _LOGGER.debug(f"Saving scene state: {scene}")
        data = {
            "scene_id": self._get_saved_scene_id(scene),
            "snapshot_entities": self.light_entity_ids,
        }
        await self.hass.services.async_call("scene", "create", data),

    async def _async_restore_scene_state(self, scene):
        _LOGGER.debug(f"Restoring scene state: {scene}")
        target = dict(entity_id=f"scene.{self._get_saved_scene_id(scene)}")
        await self.hass.services.async_call("scene", "turn_on", target=target)
        self._scene_restored = True

    def async_set_on_state(self, on: bool):
        self._model[MODEL_STATE] = on
        self._async_handle_scene_action(ACTION_ACTIVATE if on else ACTION_DEACTIVATE, self._model[MODEL_SCENE]["current"])
        self._async_data_changed()

    def async_set_current_list_val(self, type: str, value: str):
        list_model = self._model[type]
        if value not in list_model['values']:
            return

        if value == list_model['current']:
            return

        list_model['previous'] = list_model['current']
        list_model['current'] = value

        if type == MODEL_SCENE and self._model[MODEL_STATE]:
            self._save_current_scene_debouncer.async_cancel()
            self._async_handle_scene_action(ACTION_DEACTIVATE, list_model["previous"])
            self._async_handle_scene_action(ACTION_ACTIVATE, list_model["current"])
        self._async_data_changed()

    def async_set_previous_list_val(self, type: str, value: str):
        list_model = self._model[type]
        if value not in list_model['values']:
            return
        list_model['previous'] = value
        self._async_data_changed()

    def async_rollback_list_val(self, type: str):
        list_model = self._model[type]
        self.async_set_current_list_val(type, list_model['previous'])

    async def async_shutdown(self) -> None:
        """Cancel any scheduled call, and ignore new runs."""
        await super().async_shutdown()
        await self._save_current_scene_debouncer.async_shutdown()
