"""Provides device triggers for Zone Lighting."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import (
    ACTION_ACTIVATE,
    ACTION_DEACTIVATE,
    CONF_EVENT_ACTION,
    CONF_EVENT_SCENE,
    CONF_SCENES_EVENT,
    DOMAIN,
)
from .util import filter_conf_list, initialize_with_config

_LOGGER = logging.getLogger(__name__)

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Optional(CONF_TYPE): str,
        vol.Required(CONF_EVENT_ACTION): str,
        vol.Required(CONF_EVENT_SCENE): str,
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for Zone Lighting devices."""
    triggers = []

    device = dr.async_get(hass).async_get(device_id)
    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            continue

        config_data = await initialize_with_config(hass, entry)
        event_scenes = filter_conf_list(config_data[CONF_SCENES_EVENT])

        for scene in event_scenes:
            base_trigger = {
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_PLATFORM: "device",
                CONF_EVENT_SCENE: scene,
            }
            triggers.append(
                {
                    **base_trigger,
                    CONF_TYPE: f"Scene {scene} activated",
                    CONF_EVENT_ACTION: ACTION_ACTIVATE,
                }
            )
            triggers.append(
                {
                    **base_trigger,
                    CONF_TYPE: f"Scene {scene} deactivated",
                    CONF_EVENT_ACTION: ACTION_DEACTIVATE,
                }
            )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    # TODO Implement your own logic to attach triggers.
    # Use the existing state or event triggers from the automation integration.

    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: "zone_lighting_event",
            event_trigger.CONF_EVENT_DATA: {
                CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                CONF_EVENT_ACTION: config[CONF_EVENT_ACTION],
                CONF_EVENT_SCENE: config[CONF_EVENT_SCENE],
            },
        },
    )

    return await event_trigger.async_attach_trigger(
        hass,
        event_config,
        action,
        trigger_info,
        platform_type="device",
    )
