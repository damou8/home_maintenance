"""Tests for due-task notifications."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    async_mock_service,
)

from .conftest import days_ago


async def add_task(ws, title: str, interval_days: int, done_days_ago: int, **kw):
    """Add a task due in `interval_days - done_days_ago` days."""
    result = await ws(
        type="home_maintenance/add_task",
        title=title,
        interval_value=interval_days,
        interval_type="days",
        last_performed=days_ago(done_days_ago),
        **kw,
    )
    return result["id"]


async def send(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        "home_maintenance", "send_notifications", blocking=True
    )


@pytest.fixture
def notify_calls(hass: HomeAssistant):
    return async_mock_service(hass, "notify", "send_message")


async def test_due_today_overdue_and_reminder(
    hass: HomeAssistant, setup_integration, ws, notify_calls
) -> None:
    """Reminder the day before, then on the due date and while overdue."""
    await add_task(ws, "Due tomorrow", 7, 6)
    await add_task(ws, "Due today", 7, 7)
    await add_task(ws, "Late", 7, 10)
    await add_task(ws, "Not soon", 7, 2)

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
    hass: HomeAssistant, setup_integration, ws, notify_calls
) -> None:
    """Disabled tasks and tasks with notifications off send nothing."""
    task_id = await add_task(ws, "Paused", 7, 7)
    await ws(
        type="home_maintenance/update_task",
        task_id=task_id,
        updates={"enabled": False},
    )
    await add_task(ws, "Muted", 7, 7, notify_mode="none")

    await send(hass)
    assert notify_calls == []


async def test_custom_targets(
    hass: HomeAssistant, setup_integration, ws, notify_calls
) -> None:
    """A task with custom targets only notifies those."""
    await add_task(
        ws, "Car", 7, 7, notify_mode="custom", notify_targets=["notify.phone_c"]
    )
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
    hass: HomeAssistant, setup_integration, ws, notify_calls
) -> None:
    """Reminder N days before, no repeat once overdue."""
    await add_task(ws, "In three days", 10, 7)
    await add_task(ws, "Tomorrow", 10, 9)
    await add_task(ws, "Late", 10, 12)

    await send(hass)
    assert [c.data["message"] for c in notify_calls] == [
        "The task 'In three days' is due in 3 days!"
    ]


async def test_messages_follow_ha_language(
    hass: HomeAssistant, setup_integration, ws, notify_calls
) -> None:
    """Notifications use Home Assistant's language."""
    hass.config.language = "fr"
    await add_task(ws, "Nettoyage VMC", 7, 8)
    await send(hass)
    assert notify_calls[0].data["title"] == "⚠️ Information maintenance"
    assert (
        notify_calls[0].data["message"]
        == "La tâche 'Nettoyage VMC' est en retard de 1 jour !"
    )


@pytest.mark.parametrize("options", [{"notify_targets": []}])
async def test_no_default_targets(
    hass: HomeAssistant, setup_integration, ws, notify_calls
) -> None:
    """Without default targets only custom-target tasks notify."""
    await add_task(ws, "Default", 7, 7)
    await add_task(
        ws, "Custom", 7, 7, notify_mode="custom", notify_targets=["notify.phone_c"]
    )
    await send(hass)
    assert [c.data["entity_id"] for c in notify_calls] == [["notify.phone_c"]]


async def test_daily_schedule(
    hass: HomeAssistant, setup_integration, ws, notify_calls
) -> None:
    """Notifications go out at the configured time, not before."""
    await add_task(ws, "Due today", 7, 7)
    today = dt_util.now().replace(microsecond=0)

    async_fire_time_changed(hass, today.replace(hour=8, minute=59, second=59))
    await hass.async_block_till_done()
    assert notify_calls == []

    async_fire_time_changed(hass, today.replace(hour=9, minute=0, second=0))
    await hass.async_block_till_done()
    assert len(notify_calls) == 1
