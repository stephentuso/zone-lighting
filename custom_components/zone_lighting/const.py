"""Constants for Zone Lighting."""

from __future__ import annotations

from typing import Any, TypedDict

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.selector as select

NAME = "Zone Lighting"
DOMAIN = "zone_lighting"
VERSION = "0.1.0"

DOCS = {}

CONF_NAME, DEFAULT_NAME = "name", "default"
DOCS[CONF_NAME] = "Display name for this zone"

CONF_LIGHTS, DEFAULT_LIGHTS = "lights", []
DOCS[CONF_LIGHTS] = "Light entity ids this zone will control"

CONF_SCRIPTS, DEFAULT_SCRIPTS = "scripts", []
DOCS[CONF_SCRIPTS] = "Scripts to call for script scene activation/deactivation"

CONF_SCENES, DEFAULT_SCENES = "scenes", [""]
DOCS[CONF_SCENES] = "Simple scenes for this zone, state will be saved in HA scenes"

CONF_SCENES_EVENT, DEFAULT_SCENES_EVENT = "event_scenes", [""]
DOCS[CONF_SCENES_EVENT] = "Scenes that will be handled by automations"

CONF_CONTROLLERS, DEFAULT_CONTROLLERS = "controllers", [""]
DOCS[CONF_CONTROLLERS] = "Controllers for this zone"

class OptionParams(TypedDict):
    name: str
    default: Any
    validator: Any
    ui: Any
    required: bool
    schema_key: Any

def opt(name, default, validator, ui=None, required=False):
    ui = validator if ui is None else ui
    return OptionParams(
        name=name,
        default=default,
        validator=validator,
        ui=ui,
        required=required,
        schema_key=vol.Required(name, default=default) if required else vol.Optional(name, default=default),
    )

OPTIONS_LIST = [
    opt(
        CONF_LIGHTS,
        DEFAULT_LIGHTS,
        cv.entity_ids,
        select.EntitySelector(select.EntitySelectorConfig(
            domain="light",
            multiple=True,
        )),
        True,
    ),
    opt(
        CONF_SCENES,
        DEFAULT_SCENES,
        cv.ensure_list,
        select.TextSelector(select.TextSelectorConfig(
            multiple=True,
            type=select.TextSelectorType.TEXT,
        )),
        True,
    ),
    opt(
        CONF_SCENES_EVENT,
        DEFAULT_SCENES_EVENT,
        cv.ensure_list,
        select.TextSelector(select.TextSelectorConfig(
            multiple=True,
            type=select.TextSelectorType.TEXT,
        )),
        False,
    ),
    opt(
        CONF_CONTROLLERS,
        DEFAULT_CONTROLLERS,
        cv.ensure_list,
        select.TextSelector(select.TextSelectorConfig(
            multiple=True,
            type=select.TextSelectorType.TEXT,
        )),
        True,
    ),
        opt(
        CONF_SCRIPTS,
        DEFAULT_SCRIPTS,
        cv.entity_ids,
        select.EntitySelector(select.EntitySelectorConfig(
            multiple=True,
        )),
        True,
    ),
]

ACTIVATION_SWITCH = "activation_switch"
UNDO_UPDATE_LISTENER = "undo_update_listener"
COORDINATOR = "coordinator"

SELECT_SCENE = "select_scene"
SELECT_CONTROLLER = "select_controller"

ATTR_PREVIOUS_STATE = "previous_state"

MANUAL = "Manual"

ZONE_LIGHTING_EVENT = "zone_lighting_event"
CONF_EVENT_ACTION = "action"
CONF_EVENT_SCENE = "scene"
ACTION_ACTIVATE = "activate_scene"
ACTION_DEACTIVATE = "deactivate_scene"

_DOMAIN_SCHEMA = vol.Schema(
    {
        key: validator
        for key, validator in map(lambda entry: (entry['schema_key'], entry['validator']), OPTIONS_LIST)
    },
)
