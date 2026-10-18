"""Sensors with the dates of a task: when it was last done and when it's due."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONF_LAST_PERFORMED
from .entity import HomeMaintenanceEntity
from .tasks import compute_next_due, iter_tasks


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the date sensors of each task."""
    for subentry in iter_tasks(entry):
        sensors = [
            LastPerformedSensor(entry, subentry),
            NextDueSensor(entry, subentry),
        ]
        entry.runtime_data.entities.extend(sensors)
        async_add_entities(sensors, config_subentry_id=subentry.subentry_id)


class TaskDateSensor(HomeMaintenanceEntity, SensorEntity):
    """A date of the task."""

    _attr_device_class = SensorDeviceClass.DATE
    # Dates only change when the task does, which updates the entity
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the sensor."""
        super().__init__(entry, subentry)
        self._attr_unique_id = f"{self._task_id}_{self.translation_key}"


class LastPerformedSensor(TaskDateSensor):
    """The day the task was last done."""

    _attr_translation_key = "last_performed"

    def _update_state(self) -> None:
        last = dt_util.parse_datetime(self._task_data[CONF_LAST_PERFORMED])
        # Stored as local midnight, so its date is the local date
        self._attr_native_value = last.date() if last else None


class NextDueSensor(TaskDateSensor):
    """The day the task is next due."""

    _attr_translation_key = "next_due"

    def _update_state(self) -> None:
        due = compute_next_due(self._task_data)
        self._attr_native_value = due.date() if due else None
