"""ZoneLightingEntity class."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, VERSION
from .coordinator import ZoneLightingCoordinator


class ZoneLightingEntity(CoordinatorEntity):
    """ZoneLightingEntity class."""

    def __init__(self, coordinator: ZoneLightingCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=NAME,
            model=VERSION,
            manufacturer=NAME,
        )