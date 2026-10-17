"""Send notifications for due Home Maintenance tasks."""

import logging
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from . import const
from .tasks import compute_next_due, iter_tasks

_LOGGER = logging.getLogger(__name__)

# Notification texts by language, {task} is the task title and {days} a number of days
MESSAGES = {
    "en": {
        "reminder_title": "⏳ Maintenance reminder",
        "due_title": "⚠️ Maintenance due",
        "reminder_tomorrow": "The task '{task}' is due tomorrow!",
        "reminder_days": "The task '{task}' is due in {days} days!",
        "due_today": "The task '{task}' is due TODAY!",
        "overdue_one": "The task '{task}' is 1 day overdue!",
        "overdue_days": "The task '{task}' is {days} days overdue!",
    },
    "fr": {
        "reminder_title": "⏳ Rappel Maintenance",
        "due_title": "⚠️ Information maintenance",
        "reminder_tomorrow": "La tâche '{task}' est à faire demain !",
        "reminder_days": "La tâche '{task}' est à faire dans {days} jours !",
        "due_today": "La tâche '{task}' est à faire AUJOURD'HUI !",
        "overdue_one": "La tâche '{task}' est en retard de 1 jour !",
        "overdue_days": "La tâche '{task}' est en retard de {days} jours !",
    },
    "de": {
        "reminder_title": "⏳ Wartungserinnerung",
        "due_title": "⚠️ Wartung fällig",
        "reminder_tomorrow": "Die Aufgabe '{task}' ist morgen fällig!",
        "reminder_days": "Die Aufgabe '{task}' ist in {days} Tagen fällig!",
        "due_today": "Die Aufgabe '{task}' ist HEUTE fällig!",
        "overdue_one": "Die Aufgabe '{task}' ist seit 1 Tag überfällig!",
        "overdue_days": "Die Aufgabe '{task}' ist seit {days} Tagen überfällig!",
    },
}


class TaskNotifier:
    """Send a daily notification for tasks that are due soon, today or overdue."""

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

    def _message_for(self, title: str, days_left: int) -> tuple[str, str] | None:
        """Return (title, message) for a task, or None if nothing is to be sent."""
        language = (self.hass.config.language or "en").split("-")[0]
        texts = MESSAGES.get(language, MESSAGES["en"])
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
        for subentry in iter_tasks(self.entry):
            task = subentry.data
            if not task.get(const.CONF_ENABLED, True):
                continue
            targets = self._targets_for(task)
            if not targets:
                continue
            due = compute_next_due(task)
            if due is None:
                continue
            message = self._message_for(subentry.title, (due.date() - today).days)
            if message is None:
                continue

            title, text = message
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
