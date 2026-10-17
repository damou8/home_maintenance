"""Tests for enabling/disabling tasks and the task websocket API."""

from homeassistant.core import HomeAssistant

from .conftest import days_ago


async def test_disable_and_enable_task(
    hass: HomeAssistant, setup_integration, ws
) -> None:
    """A disabled task is never due and keeps its other values."""
    result = await ws(
        type="home_maintenance/add_task",
        title="Clean filter",
        interval_value=7,
        interval_type="days",
        last_performed=days_ago(10),
    )
    task_id = result["id"]
    await hass.async_block_till_done()

    entity_id = "binary_sensor.home_maintenance_clean_filter"
    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert state.attributes["enabled"] is True

    # Partial update with only "enabled" must not touch last_performed
    before = await ws(type="home_maintenance/get_task", task_id=task_id)
    await ws(
        type="home_maintenance/update_task",
        task_id=task_id,
        updates={"enabled": False},
    )
    await hass.async_block_till_done()

    task = await ws(type="home_maintenance/get_task", task_id=task_id)
    assert task["enabled"] is False
    assert task["last_performed"] == before["last_performed"]
    state = hass.states.get(entity_id)
    assert state.state == "off"
    assert state.attributes["enabled"] is False

    await ws(
        type="home_maintenance/update_task",
        task_id=task_id,
        updates={"enabled": True},
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "on"


async def test_task_notify_settings_are_stored(
    hass: HomeAssistant, setup_integration, ws
) -> None:
    """Notification overrides are saved on add and on update."""
    result = await ws(
        type="home_maintenance/add_task",
        title="Water plants",
        interval_value=3,
        interval_type="days",
        notify_mode="custom",
        notify_targets=["notify.phone_c"],
    )
    task = await ws(type="home_maintenance/get_task", task_id=result["id"])
    assert task["notify_mode"] == "custom"
    assert task["notify_targets"] == ["notify.phone_c"]
    assert task["enabled"] is True

    await ws(
        type="home_maintenance/update_task",
        task_id=result["id"],
        updates={"notify_mode": "none", "notify_targets": []},
    )
    task = await ws(type="home_maintenance/get_task", task_id=result["id"])
    assert task["notify_mode"] == "none"
    assert task["notify_targets"] == []


async def test_tasks_from_older_versions_load(
    hass: HomeAssistant, hass_storage
) -> None:
    """Tasks stored before the new fields existed get the defaults."""
    from custom_components.home_maintenance.store import TaskStore

    hass_storage["home_maintenance.storage"] = {
        "version": 1,
        "minor_version": 1,
        "key": "home_maintenance.storage",
        "data": [
            {
                "id": "home_maintenance_old",
                "title": "Old task",
                "interval_value": 1,
                "interval_type": "months",
                "last_performed": days_ago(3),
                "tag_id": None,
                "icon": "mdi:broom",
            }
        ],
    }
    store = TaskStore(hass)
    await store.async_load()
    task = store.get("home_maintenance_old")
    assert task["enabled"] is True
    assert task["notify_mode"] == "default"
    assert task["notify_targets"] == []


async def test_reset_service_with_target(
    hass: HomeAssistant, setup_integration, ws
) -> None:
    """reset_last_performed works with a single entity and with a target list."""
    for title in ("Task A", "Task B"):
        await ws(
            type="home_maintenance/add_task",
            title=title,
            interval_value=7,
            interval_type="days",
            last_performed=days_ago(10),
        )
    await hass.async_block_till_done()
    a = "binary_sensor.home_maintenance_task_a"
    b = "binary_sensor.home_maintenance_task_b"
    assert hass.states.get(a).state == "on"

    await hass.services.async_call(
        "home_maintenance", "reset_last_performed", {"entity_id": a}, blocking=True
    )
    await hass.services.async_call(
        "home_maintenance",
        "reset_last_performed",
        target={"entity_id": [b]},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(a).state == "off"
    assert hass.states.get(b).state == "off"
