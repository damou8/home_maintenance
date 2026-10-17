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
    SUBENTRY_TASK,
)


def start_of_day_iso(day: date | None = None) -> str:
    """Return local midnight of a day (today by default) as an ISO string."""
    return dt_util.start_of_local_day(day).isoformat()


def compute_next_due(task: Mapping[str, Any]) -> datetime | None:
    """Return midnight of the day a task is next due, None if unknown."""
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
    hass.config_entries.async_update_subentry(
        entry,
        subentry,
        data={**subentry.data, CONF_LAST_PERFORMED: start_of_day_iso(day)},
    )
