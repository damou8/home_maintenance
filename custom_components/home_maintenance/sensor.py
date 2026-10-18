"""Sensors of a task: when it was last done, when it's due, how much runtime is left."""

import math
from collections.abc import Callable, Mapping
from typing import Any, ClassVar

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import PERCENTAGE, Platform, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_INTERVAL_TYPE,
    CONF_INTERVAL_VALUE,
    CONF_LAST_PERFORMED,
    CONF_RUNTIME_HOURS,
    DOMAIN,
)
from .entity import HomeMaintenanceEntity
from .tasks import (
    compute_next_due,
    ha_language,
    has_interval,
    has_runtime,
    iter_tasks,
    task_id,
)

# How an interval reads, by language and unit: singular and plural, {n} the number.
# A state rather than a translated unit: Home Assistant only takes units from the
# English translations.
INTERVAL_TEXTS = {
    "en": {
        "days": ("{n} day", "{n} days"),
        "weeks": ("{n} week", "{n} weeks"),
        "months": ("{n} month", "{n} months"),
    },
    "fr": {
        "days": ("{n} jour", "{n} jours"),
        "weeks": ("{n} semaine", "{n} semaines"),
        "months": ("{n} mois", "{n} mois"),
    },
    "de": {
        "days": ("{n} Tag", "{n} Tage"),
        "weeks": ("{n} Woche", "{n} Wochen"),
        "months": ("{n} Monat", "{n} Monate"),
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors of each task."""
    ent_reg = er.async_get(hass)
    for subentry in iter_tasks(entry):
        sensors: list[TaskSensor] = [
            LastPerformedSensor(entry, subentry),
            NextDueSensor(entry, subentry),
        ]
        # The sensors of a limit only exist for a task with that limit
        for sensor_class, applies in LIMIT_SENSORS:
            if applies(subentry.data):
                sensors.append(sensor_class(entry, subentry))
                continue
            # Remove the one left over from before the limit was removed
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
    """The day the task is next due, unknown for a task without an interval."""

    _attr_device_class = SensorDeviceClass.DATE
    key = "next_due"

    def _update_state(self) -> None:
        due = compute_next_due(self._task_data)
        self._attr_native_value = due.date() if due else None


class IntervalSensor(TaskSensor):
    """How often the task repeats, as text in Home Assistant's language."""

    key = "interval"

    @property
    def native_value(self) -> str:
        """Return the interval, such as "3 months"."""
        # A property: the language needs hass, which isn't set at __init__
        count = self._task_data[CONF_INTERVAL_VALUE]
        texts = INTERVAL_TEXTS.get(ha_language(self.hass), INTERVAL_TEXTS["en"])
        singular, plural = texts[self._task_data[CONF_INTERVAL_TYPE]]
        return (singular if count == 1 else plural).format(n=count)


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


class HoursLeftSensor(TaskSensor):
    """The hours of runtime left before the task is due."""

    key = "hours_left"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_suggested_display_precision = 1
    _follows_runtime = True

    def _update_state(self) -> None:
        runtime = self._entry.runtime_data.runtime
        left = max(
            0.0, self._task_data[CONF_RUNTIME_HOURS] - runtime.used_hours(self._task_id)
        )
        # One decimal, rounded up like Remaining (after removing float noise)
        self._attr_native_value = math.ceil(round(left * 10, 6)) / 10


class LifespanSensor(TaskSensor):
    """The task's runtime limit, in hours."""

    key = "lifespan"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_suggested_display_precision = 0

    def _update_state(self) -> None:
        self._attr_native_value = self._task_data[CONF_RUNTIME_HOURS]


LIMIT_SENSORS: tuple[
    tuple[type[TaskSensor], Callable[[Mapping[str, Any]], bool]], ...
] = (
    (IntervalSensor, has_interval),
    (RemainingSensor, has_runtime),
    (HoursLeftSensor, has_runtime),
    (LifespanSensor, has_runtime),
)
