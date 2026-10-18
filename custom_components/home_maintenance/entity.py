"""Base entity for Home Maintenance tasks."""

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, NAME
from .tasks import task_id


class HomeMaintenanceEntity(Entity):
    """An entity of a task: each task is a device holding its entities."""

    _attr_has_entity_name = True
    # Whether the state depends on the hours counted for a runtime limit
    _follows_runtime = False

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the entity."""
        self._entry = entry
        self._subentry_id = subentry.subentry_id
        self._task_id = task_id(subentry)
        self._task_data = subentry.data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._task_id)},
            name=subentry.title,
            manufacturer=NAME,
            entry_type=DeviceEntryType.SERVICE,
        )
        self._update_state()

    @property
    def subentry(self) -> ConfigSubentry:
        """Return the task's current subentry."""
        return self._entry.subentries[self._subentry_id]

    async def async_added_to_hass(self) -> None:
        """Follow the runtime counter, for entities that show it."""
        await super().async_added_to_hass()
        runtime = self._entry.runtime_data.runtime
        if self._follows_runtime and runtime.has_task(self._task_id):
            self.async_on_remove(
                runtime.async_add_listener(self._task_id, self._async_runtime_updated)
            )

    def _update_state(self) -> None:
        """Compute the state from the task's data, for entities that have one."""

    @callback
    def _async_runtime_updated(self) -> None:
        self._update_state()
        self.async_write_ha_state()

    @callback
    def async_task_updated(self) -> None:
        """Refresh the state if the task's data changed (it was marked done)."""
        # An unchanged subentry keeps its data object
        if self.subentry.data is self._task_data:
            return
        self._task_data = self.subentry.data
        self._update_state()
        self.async_write_ha_state()
