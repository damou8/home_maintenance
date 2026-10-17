"""Tests for due-task notifications."""

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    async_mock_service,
)

from .conftest import add_task, update_task


def custom(*targets: str) -> dict:
    """Return the notifications section of a task with custom targets."""
    return {"notifications": {"notify_mode": "custom", "notify_targets": list(targets)}}


async def send(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        "home_maintenance", "send_notifications", blocking=True
    )


@pytest.fixture
def notify_calls(hass: HomeAssistant):
    return async_mock_service(hass, "notify", "send_message")


async def test_due_today_overdue_and_reminder(
    hass: HomeAssistant, setup_integration, notify_calls
) -> None:
    """Reminder the day before, then on the due date and while overdue."""
    await add_task(hass, setup_integration, "Due tomorrow", 7, 6)
    await add_task(hass, setup_integration, "Due today", 7, 7)
    await add_task(hass, setup_integration, "Late", 7, 10)
    await add_task(hass, setup_integration, "Not soon", 7, 2)

    await send(hass)

    sent = {c.data["message"]: c.data for c in notify_calls}
    assert set(sent) == {
        "The task 'Due tomorrow' is due tomorrow!",
        "The task 'Due today' is due TODAY!",
        "The task 'Late' is 3 days overdue!",
    }
    for data in sent.values():
        assert data["entity_id"] == ["notify.phone_a", "notify.phone_b"]
    assert sent["The task 'Late' is 3 days overdue!"]["title"] == "⚠️ Maintenance due"


async def test_disabled_and_none_tasks_are_silent(
    hass: HomeAssistant, setup_integration, notify_calls
) -> None:
    """Disabled tasks and tasks with notifications off send nothing."""
    task_id = await add_task(hass, setup_integration, "Paused", 7, 7)
    await update_task(hass, setup_integration, task_id, enabled=False)
    await add_task(
        hass, setup_integration, "Muted", 7, 7, notifications={"notify_mode": "none"}
    )

    await send(hass)
    assert notify_calls == []


async def test_custom_targets(
    hass: HomeAssistant, setup_integration, notify_calls
) -> None:
    """A task with custom targets only notifies those."""
    await add_task(hass, setup_integration, "Car", 7, 7, **custom("notify.phone_c"))
    await send(hass)
    assert len(notify_calls) == 1
    assert notify_calls[0].data["entity_id"] == ["notify.phone_c"]


@pytest.mark.parametrize(
    "options",
    [
        {
            "notify_targets": ["notify.phone_a"],
            "notify_days_before": 3,
            "notify_overdue": False,
        }
    ],
)
async def test_options_days_before_and_no_overdue(
    hass: HomeAssistant, setup_integration, notify_calls
) -> None:
    """Reminder N days before, no repeat once overdue."""
    await add_task(hass, setup_integration, "In three days", 10, 7)
    await add_task(hass, setup_integration, "Tomorrow", 10, 9)
    await add_task(hass, setup_integration, "Late", 10, 12)

    await send(hass)
    assert [c.data["message"] for c in notify_calls] == [
        "The task 'In three days' is due in 3 days!"
    ]


async def test_messages_follow_ha_language(
    hass: HomeAssistant, setup_integration, notify_calls
) -> None:
    """Notifications use Home Assistant's language."""
    hass.config.language = "fr"
    await add_task(hass, setup_integration, "Nettoyage VMC", 7, 8)
    await send(hass)
    assert notify_calls[0].data["title"] == "⚠️ Information maintenance"
    assert (
        notify_calls[0].data["message"]
        == "La tâche 'Nettoyage VMC' est en retard de 1 jour !"
    )


@pytest.mark.parametrize("options", [{"notify_targets": []}])
async def test_no_default_targets(
    hass: HomeAssistant, setup_integration, notify_calls
) -> None:
    """Without default targets only custom-target tasks notify."""
    await add_task(hass, setup_integration, "Default", 7, 7)
    await add_task(hass, setup_integration, "Custom", 7, 7, **custom("notify.phone_c"))
    await send(hass)
    assert [c.data["entity_id"] for c in notify_calls] == [["notify.phone_c"]]


async def test_daily_schedule(
    hass: HomeAssistant, setup_integration, notify_calls, freezer: FrozenDateTimeFactory
) -> None:
    """Notifications go out at the configured time, not before."""
    # Start before 9:00, or the next notification would be tomorrow's
    today = dt_util.now().replace(hour=7, minute=0, second=0, microsecond=0)
    freezer.move_to(today)
    await add_task(hass, setup_integration, "Due today", 7, 7)

    async_fire_time_changed(hass, today.replace(hour=8, minute=59, second=59))
    await hass.async_block_till_done()
    assert notify_calls == []

    async_fire_time_changed(hass, today.replace(hour=9, minute=0, second=0))
    await hass.async_block_till_done()
    assert len(notify_calls) == 1
