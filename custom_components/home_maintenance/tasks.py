"""Task helpers shared by the entities, services and notifications."""

from collections.abc import Iterator, Mapping
from datetime import date, datetime, timedelta
from typing import Any

from dateutil.relativedelta import relativedelta
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_INTERVAL_TYPE,
    CONF_INTERVAL_VALUE,
    CONF_LAST_PERFORMED,
    CONF_RUNTIME_ENTITY,
    CONF_RUNTIME_HOURS,
    SUBENTRY_TASK,
)


def ha_language(hass: HomeAssistant) -> str:
    """Return Home Assistant's language, without its region ("fr" for "fr-CA")."""
    return (hass.config.language or "en").split("-")[0]


def start_of_day_iso(day: date | None = None) -> str:
    """Return local midnight of a day (today by default) as an ISO string."""
    return dt_util.start_of_local_day(day).isoformat()


def has_interval(task: Mapping[str, Any]) -> bool:
    """Return whether a task repeats on a calendar interval."""
    return bool(task.get(CONF_INTERVAL_VALUE))


def has_runtime(task: Mapping[str, Any]) -> bool:
    """Return whether a task has a runtime limit."""
    return bool(task.get(CONF_RUNTIME_ENTITY) and task.get(CONF_RUNTIME_HOURS))


def compute_next_due(task: Mapping[str, Any]) -> datetime | None:
    """Return midnight of the day a task is next due, None if unknown or none."""
    if not has_interval(task):
        return None
    last = dt_util.parse_datetime(task[CONF_LAST_PERFORMED])
    if last is None:
        return None
    if last.tzinfo is None:
        last = dt_util.as_utc(last)

    interval_value = task[CONF_INTERVAL_VALUE]
    interval_type = task[CONF_INTERVAL_TYPE]
    if interval_type == "days":
        due = last + timedelta(days=interval_value)
    elif interval_type == "weeks":
        due = last + timedelta(weeks=interval_value)
    elif interval_type == "months":
        due = last + relativedelta(months=interval_value)
    else:
        due = last
    return due.replace(hour=0, minute=0, second=0, microsecond=0)


def task_id(subentry: ConfigSubentry) -> str:
    """Return the stable ID of a task, used in its entities' unique IDs."""
    return subentry.unique_id or subentry.subentry_id


def iter_tasks(entry: ConfigEntry) -> Iterator[ConfigSubentry]:
    """Iterate over the tasks of a config entry."""
    for subentry in entry.subentries.values():
        if subentry.subentry_type == SUBENTRY_TASK:
            yield subentry


@callback
def async_mark_done(
    hass: HomeAssistant,
    entry: ConfigEntry,
    subentry: ConfigSubentry,
    day: date | None = None,
) -> None:
    """Record that a task was done on a day, today by default."""
    # Done again on the same day leaves the data unchanged: reset the runtime here
    entry.runtime_data.runtime.async_set_used(task_id(subentry), 0)
    hass.config_entries.async_update_subentry(
        entry,
        subentry,
        data={**subentry.data, CONF_LAST_PERFORMED: start_of_day_iso(day)},
    )
