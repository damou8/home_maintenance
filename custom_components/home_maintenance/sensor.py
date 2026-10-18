"""Sensors of a task: when it was last done, when it's due, how much runtime is left."""

import math
from typing import ClassVar

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import PERCENTAGE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONF_LAST_PERFORMED, CONF_RUNTIME_HOURS, DOMAIN
from .entity import HomeMaintenanceEntity
from .tasks import compute_next_due, has_interval, has_runtime, iter_tasks, task_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors of each task."""
    ent_reg = er.async_get(hass)
    for subentry in iter_tasks(entry):
        sensors: list[TaskSensor] = [LastPerformedSensor(entry, subentry)]
        # The other sensors only exist for the limits the task has
        for sensor_class, applies in (
            (NextDueSensor, has_interval(subentry.data)),
            (RemainingSensor, has_runtime(subentry.data)),
        ):
            if applies:
                sensors.append(sensor_class(entry, subentry))
                continue
            # Remove the one left over from before the task was changed
            unique_id = f"{task_id(subentry)}_{sensor_class.key}"
            if entity_id := ent_reg.async_get_entity_id(
                Platform.SENSOR, DOMAIN, unique_id
            ):
                ent_reg.async_remove(entity_id)
        entry.runtime_data.entities.extend(sensors)
        async_add_entities(sensors, config_subentry_id=subentry.subentry_id)


class TaskSensor(HomeMaintenanceEntity, SensorEntity):
    """A sensor of a task."""

    # The values only change when the task does, which updates the entity
    _attr_should_poll = False
    # Translation key and end of the unique ID. A plain class attribute: Home
    # Assistant turns _attr_translation_key into a property of the class
    key: ClassVar[str]

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the sensor."""
        self._attr_translation_key = self.key
        super().__init__(entry, subentry)
        self._attr_unique_id = f"{self._task_id}_{self.key}"


class LastPerformedSensor(TaskSensor):
    """The day the task was last done."""

    _attr_device_class = SensorDeviceClass.DATE
    key = "last_performed"

    def _update_state(self) -> None:
        last = dt_util.parse_datetime(self._task_data[CONF_LAST_PERFORMED])
        # Stored as local midnight, so its date is the local date
        self._attr_native_value = last.date() if last else None


class NextDueSensor(TaskSensor):
    """The day the task is next due."""

    _attr_device_class = SensorDeviceClass.DATE
    key = "next_due"

    def _update_state(self) -> None:
        due = compute_next_due(self._task_data)
        self._attr_native_value = due.date() if due else None


class RemainingSensor(TaskSensor):
    """The share of the task's runtime limit that is left."""

    key = "remaining"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0
    # Also updated by the runtime counter while the entity is on
    _follows_runtime = True

    def _update_state(self) -> None:
        runtime = self._entry.runtime_data.runtime
        # One decimal, rounded up so it only reads 0 once the limit is reached
        self._attr_native_value = math.ceil(runtime.remaining(self._task_id) * 10) / 10
        self._attr_extra_state_attributes = {
            "hours_used": round(runtime.used_hours(self._task_id), 1),
            "hours_limit": self._task_data[CONF_RUNTIME_HOURS],
        }
