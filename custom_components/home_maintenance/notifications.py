"""Send notifications for due Home Maintenance tasks."""

import logging
import math
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from . import const
from .tasks import compute_next_due, ha_language, iter_tasks, task_id

_LOGGER = logging.getLogger(__name__)

# Notification texts by language: {task} is the task title, {days} a number of
# days, {pct} the percentage of runtime left and {hours} a number of hours
MESSAGES = {
    "en": {
        "reminder_title": "⏳ Maintenance reminder",
        "due_title": "⚠️ Maintenance due",
        "reminder_tomorrow": "The task '{task}' is due tomorrow!",
        "reminder_days": "The task '{task}' is due in {days} days!",
        "due_today": "The task '{task}' is due TODAY!",
        "overdue_one": "The task '{task}' is 1 day overdue!",
        "overdue_days": "The task '{task}' is {days} days overdue!",
        "runtime_low": "The task '{task}' has {pct}% of its runtime left ({hours} h)!",
        "runtime_over": "The task '{task}' reached its {hours} hours of runtime!",
    },
    "fr": {
        "reminder_title": "⏳ Rappel Maintenance",
        "due_title": "⚠️ Information maintenance",
        "reminder_tomorrow": "La tâche '{task}' est à faire demain !",
        "reminder_days": "La tâche '{task}' est à faire dans {days} jours !",
        "due_today": "La tâche '{task}' est à faire AUJOURD'HUI !",
        "overdue_one": "La tâche '{task}' est en retard de 1 jour !",
        "overdue_days": "La tâche '{task}' est en retard de {days} jours !",
        "runtime_low": (
            "La tâche '{task}' n'a plus que {pct} % d'utilisation ({hours} h) !"
        ),
        "runtime_over": (
            "La tâche '{task}' a atteint ses {hours} heures d'utilisation !"
        ),
    },
    "de": {
        "reminder_title": "⏳ Wartungserinnerung",
        "due_title": "⚠️ Wartung fällig",
        "reminder_tomorrow": "Die Aufgabe '{task}' ist morgen fällig!",
        "reminder_days": "Die Aufgabe '{task}' ist in {days} Tagen fällig!",
        "due_today": "Die Aufgabe '{task}' ist HEUTE fällig!",
        "overdue_one": "Die Aufgabe '{task}' ist seit 1 Tag überfällig!",
        "overdue_days": "Die Aufgabe '{task}' ist seit {days} Tagen überfällig!",
        "runtime_low": (
            "Die Aufgabe '{task}' hat noch {pct} % ihrer Laufzeit ({hours} Std.)!"
        ),
        "runtime_over": (
            "Die Aufgabe '{task}' hat ihre {hours} Betriebsstunden erreicht!"
        ),
    },
}


# Date reminders go out in a daily check. Runtime warnings go out as soon as the
# remaining runtime crosses the threshold or reaches 0, and the daily check
# repeats the latter until the task is done.
class TaskNotifier:
    """Notify about tasks that are due soon, due or overdue."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the notifier."""
        self.hass = hass
        self.entry = entry

    @property
    def _options(self) -> dict:
        return self.entry.options

    @callback
    def async_start(self) -> Callable[[], None]:
        """Schedule the daily check, return the function that cancels it."""
        notify_time = dt_util.parse_time(
            self._options.get(const.CONF_NOTIFY_TIME, const.DEFAULT_NOTIFY_TIME)
        ) or dt_util.parse_time(const.DEFAULT_NOTIFY_TIME)

        async def _handle_time(_now: datetime) -> None:
            await self.async_send_notifications()

        return async_track_time_change(
            self.hass,
            _handle_time,
            hour=notify_time.hour,
            minute=notify_time.minute,
            second=notify_time.second,
        )

    def _targets_for(self, task: Mapping[str, Any]) -> list[str]:
        """Return the notify entities a task's notifications go to."""
        mode = task.get(const.CONF_NOTIFY_MODE, const.NOTIFY_MODE_DEFAULT)
        if mode == const.NOTIFY_MODE_NONE:
            return []
        if mode == const.NOTIFY_MODE_CUSTOM:
            return task.get(const.CONF_NOTIFY_TARGETS) or []
        return self._options.get(const.CONF_NOTIFY_TARGETS) or []

    def _texts(self) -> dict[str, str]:
        """Return the notification texts in Home Assistant's language."""
        return MESSAGES.get(ha_language(self.hass), MESSAGES["en"])

    def _runtime_threshold(self, task: Mapping[str, Any]) -> int:
        """Return the remaining percentage that triggers a task's warning."""
        threshold = task.get(const.CONF_NOTIFY_RUNTIME_THRESHOLD)
        if threshold is None:
            threshold = self._options.get(
                const.CONF_NOTIFY_RUNTIME_THRESHOLD,
                const.DEFAULT_NOTIFY_RUNTIME_THRESHOLD,
            )
        return int(threshold)

    def _runtime_message(
        self, subentry: ConfigSubentry, remaining: float
    ) -> tuple[str, str]:
        """Return (title, message) about a task's runtime."""
        texts = self._texts()
        limit = subentry.data[const.CONF_RUNTIME_HOURS]
        if remaining <= 0:
            return texts["due_title"], texts["runtime_over"].format(
                task=subentry.title, hours=limit
            )
        return texts["reminder_title"], texts["runtime_low"].format(
            task=subentry.title,
            pct=math.ceil(remaining),
            hours=math.ceil(limit * remaining / 100),
        )

    @callback
    def async_runtime_changed(
        self, subentry: ConfigSubentry, previous: float, remaining: float
    ) -> None:
        """Warn as soon as a task's runtime crosses its threshold, or runs out."""
        threshold = self._runtime_threshold(subentry.data)
        crossed_zero = previous > 0 >= remaining
        crossed_threshold = threshold > 0 and previous > threshold >= remaining
        if not (crossed_zero or crossed_threshold):
            return
        self.entry.async_create_task(
            self.hass,
            self._async_send(subentry, *self._runtime_message(subentry, remaining)),
        )

    def _message_for(self, title: str, days_left: int) -> tuple[str, str] | None:
        """Return (title, message) for a task, or None if nothing is to be sent."""
        texts = self._texts()
        days_before = int(
            self._options.get(
                const.CONF_NOTIFY_DAYS_BEFORE, const.DEFAULT_NOTIFY_DAYS_BEFORE
            )
        )
        overdue = self._options.get(
            const.CONF_NOTIFY_OVERDUE, const.DEFAULT_NOTIFY_OVERDUE
        )
        if days_left > 0:
            if days_left != days_before:
                return None
            key = "reminder_tomorrow" if days_left == 1 else "reminder_days"
            return texts["reminder_title"], texts[key].format(
                task=title, days=days_left
            )
        if days_left == 0:
            return texts["due_title"], texts["due_today"].format(task=title)
        if not overdue:
            return None
        key = "overdue_one" if days_left == -1 else "overdue_days"
        return texts["due_title"], texts[key].format(task=title, days=-days_left)

    async def async_send_notifications(self) -> None:
        """Notify about every enabled task that is due soon, today or overdue."""
        today = dt_util.now().date()
        runtime = self.entry.runtime_data.runtime
        for subentry in iter_tasks(self.entry):
            tid = task_id(subentry)
            # Out of runtime: that's the task's one reminder, whatever its date
            if runtime.has_task(tid) and runtime.remaining(tid) <= 0:
                message = self._runtime_message(subentry, 0)
            elif (due := compute_next_due(subentry.data)) is not None:
                message = self._message_for(subentry.title, (due.date() - today).days)
            else:
                message = None
            if message is not None:
                await self._async_send(subentry, *message)

    async def _async_send(
        self, subentry: ConfigSubentry, title: str, text: str
    ) -> None:
        """Send a notification about a task, unless it's disabled or muted."""
        task = subentry.data
        if not task.get(const.CONF_ENABLED, True):
            return
        if not (targets := self._targets_for(task)):
            return
        try:
            await self.hass.services.async_call(
                "notify",
                "send_message",
                {"title": title, "message": text},
                target={"entity_id": targets},
                blocking=True,
            )
        except HomeAssistantError:
            _LOGGER.exception("Failed to send notification for %s", subentry.title)
