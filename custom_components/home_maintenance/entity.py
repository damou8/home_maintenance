"""Base entity for Home Maintenance tasks."""

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, NAME
from .tasks import task_id


class HomeMaintenanceEntity(Entity):
    """An entity of a task: each task is a device holding its entities."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the entity."""
        self._entry = entry
        self._subentry_id = subentry.subentry_id
        self._task_id = task_id(subentry)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._task_id)},
            name=subentry.title,
            manufacturer=NAME,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def subentry(self) -> ConfigSubentry:
        """Return the task's current subentry."""
        return self._entry.subentries[self._subentry_id]
