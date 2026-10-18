"""Tests for tasks with a runtime limit."""

from datetime import timedelta
from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.const import (
    EVENT_HOMEASSISTANT_FINAL_WRITE,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.home_maintenance.const import DOMAIN

from .conftest import add_task, days_ago, update_task

AC = "climate.living_room"


def limit(hours: int = 100, entity: str = AC, **extra: Any) -> dict[str, Any]:
    """Return the runtime section of a task form."""
    return {"runtime": {"runtime_entity": entity, "runtime_hours": hours, **extra}}


async def add_filter(
    hass: HomeAssistant, entry, title: str = "AC filter", **fields: Any
) -> str:
    """Add a task with a 100 h runtime limit and no interval."""
    return await add_task(
        hass, entry, title, interval_days=None, **{**limit(), **fields}
    )


async def run(hass: HomeAssistant, freezer: FrozenDateTimeFactory, hours: float):
    """Let time pass and the counter's timer fire."""
    freezer.tick(timedelta(hours=hours))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def remaining(hass: HomeAssistant, entity_id: str = "sensor.ac_filter_remaining"):
    return float(hass.states.get(entity_id).state)


@pytest.fixture(autouse=True)
def morning(freezer: FrozenDateTimeFactory) -> None:
    """Start at 10:00, an hour after the daily check, which then doesn't interfere."""
    freezer.move_to("2026-10-19T10:00:00-07:00")


@pytest.fixture(autouse=True)
def notify_calls(hass: HomeAssistant):
    return async_mock_service(hass, "notify", "send_message")


async def submit(hass: HomeAssistant, entry, data: dict[str, Any]) -> dict:
    """Submit the Add task form."""
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "task"), context={"source": SOURCE_USER}
    )
    return await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "title": "AC filter",
            "interval_type": "days",
            "notifications": {"notify_mode": "default"},
            **data,
        },
    )


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({"runtime": {}}, "no_limit"),
        ({"runtime": {"runtime_hours": 100}}, "no_limit"),
        ({"runtime": {"runtime_entity": AC}}, "no_runtime_hours"),
    ],
)
async def test_form_needs_a_limit(
    hass: HomeAssistant, setup_integration, data, error
) -> None:
    """A task needs an interval or a runtime limit, which needs hours."""
    result = await submit(hass, setup_integration, data)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_counts_only_while_on(
    hass: HomeAssistant, setup_integration, freezer: FrozenDateTimeFactory
) -> None:
    """Runtime counts in any state but off, unavailable or unknown."""
    entry = setup_integration
    hass.states.async_set(AC, "off")
    subentry_id = await add_filter(hass, entry)

    assert entry.subentries[subentry_id].data["interval_value"] is None
    assert remaining(hass) == 100
    # No interval: no due date, and not due by date
    assert hass.states.get("sensor.ac_filter_next_due").state == "unknown"
    assert hass.states.get("binary_sensor.ac_filter").state == "off"
    lifespan = hass.states.get("sensor.ac_filter_lifespan")
    assert lifespan.state == "100"
    assert lifespan.attributes["unit_of_measurement"] == "h"

    hass.states.async_set(AC, "cool")
    await run(hass, freezer, 20)
    hass.states.async_set(AC, "fan_only")
    await run(hass, freezer, 5)
    assert remaining(hass) == 75
    assert hass.states.get("sensor.ac_filter_remaining").attributes == {
        "hours_used": 25.0,
        "hours_limit": 100,
        "unit_of_measurement": "%",
        "friendly_name": "AC filter Remaining",
    }
    hours_left = hass.states.get("sensor.ac_filter_hours_left")
    assert hours_left.state == "75.0"
    assert hours_left.attributes["device_class"] == "duration"

    for state in ("off", "unavailable", "unknown"):
        hass.states.async_set(AC, state)
        await run(hass, freezer, 10)
    assert remaining(hass) == 75

    hass.states.async_set(AC, "heat")
    await run(hass, freezer, 80)
    assert remaining(hass) == 0
    due = hass.states.get("binary_sensor.ac_filter")
    assert due.state == "on"
    assert due.attributes["runtime_remaining"] == 0
    assert due.attributes["runtime_left"] == 0
    assert due.attributes["runtime_entity"] == AC


async def test_mark_done_resets(
    hass: HomeAssistant, setup_integration, freezer: FrozenDateTimeFactory
) -> None:
    """Marking done resets the runtime, also when done the same day."""
    entry = setup_integration
    hass.states.async_set(AC, "cool")
    await add_filter(hass, entry, **limit(10))
    await run(hass, freezer, 6)
    assert remaining(hass) == 40

    # Added today, done today: the task's data doesn't change
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.ac_filter_mark_done"}, blocking=True
    )
    await hass.async_block_till_done()
    assert remaining(hass) == 100

    # Still counting, from the reset
    await run(hass, freezer, 1)
    assert remaining(hass) == 90
    assert hass.states.get("binary_sensor.ac_filter").attributes["runtime_left"] == 9


async def test_hybrid_due_first(
    hass: HomeAssistant, setup_integration, freezer: FrozenDateTimeFactory
) -> None:
    """A task with both limits is due at whichever comes first."""
    entry = setup_integration
    hass.states.async_set(AC, "cool")
    await add_task(hass, entry, "By date", 30, 40, **limit())
    await add_task(hass, entry, "By runtime", 30, 0, **limit(10))
    assert hass.states.get("binary_sensor.by_date").state == "on"
    assert hass.states.get("binary_sensor.by_runtime").state == "off"
    assert hass.states.get("sensor.by_runtime_next_due").state == days_ago(-30)

    await run(hass, freezer, 10)
    assert hass.states.get("binary_sensor.by_runtime").state == "on"
    assert remaining(hass, "sensor.by_date_remaining") == 90


async def test_hours_survive_reload_and_restart(
    hass: HomeAssistant,
    setup_integration,
    freezer: FrozenDateTimeFactory,
    hass_storage: dict[str, Any],
) -> None:
    """The counter is saved, including the hours already used."""
    entry = setup_integration
    hass.states.async_set(AC, "cool")
    subentry_id = await add_filter(hass, entry, **limit(runtime_used=30))
    assert remaining(hass) == 70

    await run(hass, freezer, 10)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert remaining(hass) == 60

    task_id = entry.subentries[subentry_id].unique_id
    assert hass_storage[f"{DOMAIN}.runtime"]["data"] == {task_id: 40 * 3600}

    # Saved when Home Assistant stops
    await run(hass, freezer, 5)
    hass.set_state(CoreState.stopping)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)
    await hass.async_block_till_done()
    hass.set_state(CoreState.running)
    assert hass_storage[f"{DOMAIN}.runtime"]["data"] == {task_id: 45 * 3600}


async def test_change_form_corrects_hours(
    hass: HomeAssistant, setup_integration, freezer: FrozenDateTimeFactory
) -> None:
    """The change form shows the hours used and applies a correction."""
    entry = setup_integration
    hass.states.async_set(AC, "cool")
    subentry_id = await add_filter(hass, entry)
    await run(hass, freezer, 12.34)

    async def reconfigure(used: float, shown: float) -> None:
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, "task"),
            context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry_id},
        )
        schema = result["data_schema"].schema
        section = next(v for k, v in schema.items() if k == "runtime")
        suggested = next(
            k.description["suggested_value"]
            for k in section.schema.schema
            if k == "runtime_used"
        )
        assert suggested == shown
        # Time passes while the form is open
        await run(hass, freezer, 1)
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                "title": "AC filter",
                "interval_type": "days",
                "last_performed": days_ago(0),
                "enabled": True,
                **limit(runtime_used=used),
                "notifications": {"notify_mode": "default"},
            },
        )
        assert result["type"] is FlowResultType.ABORT
        await hass.async_block_till_done()

    # Unchanged: the hours counted while the form was open are kept
    await reconfigure(12.3, shown=12.3)
    assert remaining(hass) == 86.7

    await reconfigure(50, shown=13.3)
    assert remaining(hass) == 50


async def test_removed_limits_remove_their_sensors(
    hass: HomeAssistant, setup_integration
) -> None:
    """A limit's sensors go with it; Next due always stays."""
    entry = setup_integration
    ent_reg = er.async_get(hass)
    runtime_sensors = [
        f"sensor.ac_filter_{key}" for key in ("remaining", "hours_left", "lifespan")
    ]
    subentry_id = await add_task(hass, entry, "AC filter", 30, 0, **limit())
    assert all(ent_reg.async_get(entity_id) for entity_id in runtime_sensors)

    await update_task(hass, entry, subentry_id, runtime_entity=None)
    assert not any(ent_reg.async_get(entity_id) for entity_id in runtime_sensors)
    assert (
        "runtime_remaining" not in hass.states.get("binary_sensor.ac_filter").attributes
    )

    assert ent_reg.async_get("sensor.ac_filter_interval")

    await update_task(hass, entry, subentry_id, runtime_entity=AC, interval_value=None)
    assert all(ent_reg.async_get(entity_id) for entity_id in runtime_sensors)
    assert ent_reg.async_get("sensor.ac_filter_interval") is None
    assert hass.states.get("sensor.ac_filter_next_due").state == "unknown"


async def test_notifications(
    hass: HomeAssistant,
    setup_integration,
    freezer: FrozenDateTimeFactory,
    notify_calls,
) -> None:
    """A warning once below the threshold, then at 0% and every morning."""
    entry = setup_integration
    hass.states.async_set(AC, "cool")
    await add_filter(hass, entry, **limit(10))

    await run(hass, freezer, 8.5)
    assert notify_calls == []
    await run(hass, freezer, 0.6)
    await run(hass, freezer, 0.5)
    assert [c.data["message"] for c in notify_calls] == [
        "The task 'AC filter' has 9% of its runtime left (1 h)!"
    ]
    assert notify_calls[0].data["entity_id"] == ["notify.phone_a", "notify.phone_b"]
    assert notify_calls[0].data["title"] == "⏳ Maintenance reminder"

    notify_calls.clear()
    await run(hass, freezer, 1)
    await run(hass, freezer, 1)
    assert [c.data["message"] for c in notify_calls] == [
        "The task 'AC filter' reached its 10 hours of runtime!"
    ]
    assert notify_calls[0].data["title"] == "⚠️ Maintenance due"

    # Repeated by the daily check until done
    notify_calls.clear()
    await hass.services.async_call(DOMAIN, "send_notifications", blocking=True)
    assert [c.data["message"] for c in notify_calls] == [
        "The task 'AC filter' reached its 10 hours of runtime!"
    ]


async def test_runtime_message_replaces_date_message(
    hass: HomeAssistant,
    setup_integration,
    freezer: FrozenDateTimeFactory,
    notify_calls,
) -> None:
    """A task out of runtime gets one notification per morning, not two."""
    hass.states.async_set(AC, "cool")
    await add_task(hass, setup_integration, "AC filter", 7, 7, **limit(10))
    await run(hass, freezer, 11)

    notify_calls.clear()
    await hass.services.async_call(DOMAIN, "send_notifications", blocking=True)
    assert [c.data["message"] for c in notify_calls] == [
        "The task 'AC filter' reached its 10 hours of runtime!"
    ]


@pytest.mark.parametrize(
    "options",
    [
        {
            "notify_targets": ["notify.phone_a"],
            "notify_time": "09:00:00",
            "notify_days_before": 1,
            "notify_overdue": True,
            "notify_runtime_threshold": 30,
        }
    ],
)
async def test_thresholds(
    hass: HomeAssistant,
    setup_integration,
    freezer: FrozenDateTimeFactory,
    notify_calls,
) -> None:
    """The default threshold comes from the options; a task can override it."""
    entry = setup_integration
    hass.states.async_set(AC, "cool")
    await add_filter(hass, entry, "Default")
    await add_filter(
        hass,
        entry,
        "Override",
        notifications={"notify_mode": "default", "notify_runtime_threshold": 50},
    )
    await add_filter(
        hass,
        entry,
        "Off",
        notifications={"notify_mode": "default", "notify_runtime_threshold": 0},
    )
    paused = await add_filter(hass, entry, "Paused")
    await update_task(hass, entry, paused, enabled=False)

    await run(hass, freezer, 50)
    assert [c.data["message"] for c in notify_calls] == [
        "The task 'Override' has 50% of its runtime left (50 h)!"
    ]
    notify_calls.clear()
    await run(hass, freezer, 20)
    assert [c.data["message"] for c in notify_calls] == [
        "The task 'Default' has 30% of its runtime left (30 h)!"
    ]
    # Disabled: counted, but silent and never due
    assert remaining(hass, "sensor.paused_remaining") == 30
    await run(hass, freezer, 30)
    assert hass.states.get("binary_sensor.paused").state == "off"
    assert "Paused" not in str([c.data for c in notify_calls])


@pytest.mark.parametrize(
    "options",
    [
        {
            "notify_targets": ["notify.phone_a"],
            "notify_time": "09:00:00",
            "notify_days_before": 1,
            "notify_overdue": False,
        }
    ],
)
async def test_no_daily_repeat_without_overdue_option(
    hass: HomeAssistant,
    setup_integration,
    freezer: FrozenDateTimeFactory,
    notify_calls,
) -> None:
    """With overdue repeats off, running out is notified once, not every morning."""
    hass.states.async_set(AC, "cool")
    await add_filter(hass, setup_integration, **limit(10))
    await run(hass, freezer, 11)
    # Crossing the threshold and 0 at once: one notification
    assert [c.data["message"] for c in notify_calls] == [
        "The task 'AC filter' reached its 10 hours of runtime!"
    ]

    notify_calls.clear()
    await hass.services.async_call(DOMAIN, "send_notifications", blocking=True)
    assert notify_calls == []


def issue(hass: HomeAssistant, entry, subentry_id: str) -> ir.IssueEntry | None:
    """Return the missing-entity repair issue of a task."""
    task_id = entry.subentries[subentry_id].unique_id
    return ir.async_get(hass).async_get_issue(
        DOMAIN, f"missing_runtime_entity_{task_id}"
    )


async def test_missing_entity_repair_issue(
    hass: HomeAssistant, setup_integration
) -> None:
    """A repair issue tells when the counted entity is renamed, removed or missing."""
    entry = setup_integration
    ent_reg = er.async_get(hass)
    ent_reg.async_get_or_create(
        "climate", "test", "ac", suggested_object_id="living_room"
    )
    hass.states.async_set(AC, "cool")
    ac_task = await add_filter(hass, entry)
    assert issue(hass, entry, ac_task) is None

    # Renamed, which also moves its state: the task still counts the old ID
    ent_reg.async_update_entity(AC, new_entity_id="climate.salon")
    hass.states.async_remove(AC)
    await hass.async_block_till_done()
    found = issue(hass, entry, ac_task)
    assert found.translation_placeholders == {"task": "AC filter", "entity_id": AC}
    # Back under its old ID
    hass.states.async_set(AC, "cool")
    await hass.async_block_till_done()
    assert issue(hass, entry, ac_task) is None

    # Removed, then created again
    ent_reg.async_get_or_create(
        "switch", "test", "dh", suggested_object_id="dehumidifier"
    )
    dh_task = await add_filter(
        hass, entry, "Dehumidifier filter", **limit(entity="switch.dehumidifier")
    )
    ent_reg.async_remove("switch.dehumidifier")
    await hass.async_block_till_done()
    assert issue(hass, entry, dh_task)
    ent_reg.async_get_or_create(
        "switch", "test", "dh", suggested_object_id="dehumidifier"
    )
    await hass.async_block_till_done()
    assert issue(hass, entry, dh_task) is None

    # Missing from the start, then the task is deleted
    fan_task = await add_filter(
        hass, entry, "Fan filter", **limit(entity="fan.nothing")
    )
    assert issue(hass, entry, fan_task)
    task_id = entry.subentries[fan_task].unique_id
    assert hass.config_entries.async_remove_subentry(entry, fan_task)
    await hass.async_block_till_done()
    assert not ir.async_get(hass).async_get_issue(
        DOMAIN, f"missing_runtime_entity_{task_id}"
    )
