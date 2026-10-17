"""Buttons that mark a task as done."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import HomeMaintenanceEntity
from .tasks import async_mark_done, iter_tasks


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one button per task."""
    for subentry in iter_tasks(entry):
        async_add_entities(
            [MarkDoneButton(entry, subentry)], config_subentry_id=subentry.subentry_id
        )


class MarkDoneButton(HomeMaintenanceEntity, ButtonEntity):
    """Mark the task as done today."""

    _attr_translation_key = "mark_done"

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the button."""
        super().__init__(entry, subentry)
        self._attr_unique_id = f"{self._task_id}_mark_done"

    async def async_press(self) -> None:
        """Mark the task as done today."""
        async_mark_done(self.hass, self._entry, self.subentry)
