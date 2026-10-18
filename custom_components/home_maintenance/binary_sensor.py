"""Binary sensors that turn on when a task is due."""

import math

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ENABLED,
    CONF_ICON,
    CONF_INTERVAL_TYPE,
    CONF_INTERVAL_VALUE,
    CONF_LAST_PERFORMED,
    CONF_RUNTIME_ENTITY,
    CONF_RUNTIME_HOURS,
    CONF_TAG_ID,
    DEFAULT_ICON,
)
from .entity import HomeMaintenanceEntity
from .tasks import compute_next_due, has_interval, iter_tasks


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one binary sensor per task."""
    for subentry in iter_tasks(entry):
        sensor = HomeMaintenanceSensor(entry, subentry)
        entry.runtime_data.entities.append(sensor)
        async_add_entities([sensor], config_subentry_id=subentry.subentry_id)


class HomeMaintenanceSensor(HomeMaintenanceEntity, BinarySensorEntity):
    """On when the task is due, by date or by runtime."""

    # Named after its device, which is the task
    _attr_name = None
    _follows_runtime = True

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the sensor."""
        super().__init__(entry, subentry)
        self._attr_unique_id = self._task_id

    def _update_state(self) -> None:
        """Compute the state from the task's data."""
        task = self._task_data
        enabled = task.get(CONF_ENABLED, True)
        due = compute_next_due(task)
        runtime = self._entry.runtime_data.runtime
        counted = runtime.has_task(self._task_id)

        # A task with an interval but no valid date is always due by date
        if not has_interval(task):
            due_by_date = False
        elif due is None:
            due_by_date = True
        else:
            today = dt_util.now().replace(hour=0, minute=0, second=0, microsecond=0)
            due_by_date = today >= due
        worn_out = counted and runtime.remaining(self._task_id) <= 0
        # A disabled task is never reported as due
        self._attr_is_on = enabled and (due_by_date or worn_out)

        self._attr_icon = task.get(CONF_ICON) or DEFAULT_ICON
        self._attr_extra_state_attributes = {
            "last_performed": task[CONF_LAST_PERFORMED],
            "interval_value": task[CONF_INTERVAL_VALUE],
            "interval_type": task[CONF_INTERVAL_TYPE],
            "next_due": due.isoformat() if due else "unknown",
            "enabled": enabled,
        }
        if task.get(CONF_TAG_ID):
            self._attr_extra_state_attributes["tag_id"] = task[CONF_TAG_ID]
        if counted:
            limit = task[CONF_RUNTIME_HOURS]
            used = runtime.used_hours(self._task_id)
            # Rounded up, so they only read 0 once the limit is reached
            self._attr_extra_state_attributes |= {
                "runtime_entity": task[CONF_RUNTIME_ENTITY],
                "runtime_limit": limit,
                "runtime_remaining": math.ceil(runtime.remaining(self._task_id)),
                "runtime_left": max(0, math.ceil(limit - used)),
            }

    async def async_update(self) -> None:
        """Recompute the state: a task becomes due as days pass."""
        self._update_state()
