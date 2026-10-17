"""Tests for task entities, marking tasks done and removing them."""

import pytest
from homeassistant.components.tag.const import EVENT_TAG_SCANNED
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.home_maintenance.const import DOMAIN

from .conftest import add_task, days_ago, update_task


async def test_due_state_and_disable(hass: HomeAssistant, setup_integration) -> None:
    """A task is due once its interval has passed, never while disabled."""
    entry = setup_integration
    late = await add_task(hass, entry, "Late", 7, 10)
    await add_task(hass, entry, "Recent", 7, 2)
    assert hass.states.get("binary_sensor.late").state == "on"
    assert hass.states.get("binary_sensor.recent").state == "off"

    await update_task(hass, entry, late, enabled=False)
    state = hass.states.get("binary_sensor.late")
    assert state.state == "off"
    assert state.attributes["enabled"] is False


async def test_mark_done_button(hass: HomeAssistant, setup_integration) -> None:
    """The button marks the task done today, without reloading the entry."""
    entry = setup_integration
    subentry_id = await add_task(hass, entry, "Clean filter", 7, 10)
    sensor = entry.runtime_data.sensors[subentry_id]

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.clean_filter_mark_done"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.subentries[subentry_id].data["last_performed"].startswith(days_ago(0))
    assert hass.states.get("binary_sensor.clean_filter").state == "off"
    # Updated in place: same entity object
    assert entry.runtime_data.sensors[subentry_id] is sensor


async def test_reset_action(hass: HomeAssistant, setup_integration) -> None:
    """The action accepts one entity or a target, with an optional date."""
    entry = setup_integration
    a = await add_task(hass, entry, "Task A", 7, 10)
    b = await add_task(hass, entry, "Task B", 7, 10)

    await hass.services.async_call(
        DOMAIN,
        "reset_last_performed",
        {"entity_id": "binary_sensor.task_a", "performed_date": days_ago(2)},
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN,
        "reset_last_performed",
        target={"entity_id": ["button.task_b_mark_done"]},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.subentries[a].data["last_performed"].startswith(days_ago(2))
    assert entry.subentries[b].data["last_performed"].startswith(days_ago(0))
    assert hass.states.get("binary_sensor.task_a").state == "off"
    assert hass.states.get("binary_sensor.task_b").state == "off"


async def test_reset_action_rejects_other_entities(
    hass: HomeAssistant, setup_integration
) -> None:
    """Marking done an entity that isn't a task is an error."""
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "reset_last_performed",
            {"entity_id": "light.kitchen"},
            blocking=True,
        )


async def test_delete_task(hass: HomeAssistant, setup_integration) -> None:
    """Deleting a task removes its entities and device."""
    entry = setup_integration
    subentry_id = await add_task(hass, entry, "Clean filter", 7, 10)
    task_id = entry.subentries[subentry_id].unique_id

    assert hass.config_entries.async_remove_subentry(entry, subentry_id)
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.clean_filter") is None
    assert er.async_get(hass).async_get("binary_sensor.clean_filter") is None
    assert not dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, task_id), entry.entry_id
    )


async def test_tag_scan_marks_done(hass: HomeAssistant, setup_integration) -> None:
    """Scanning a task's NFC tag marks it done."""
    entry = setup_integration
    tag = er.async_get(hass).async_get_or_create("tag", "tag", "tag-uuid-1")
    subentry_id = await add_task(
        hass, entry, "Descale kettle", 30, 40, tag_id=tag.entity_id
    )
    assert hass.states.get("binary_sensor.descale_kettle").state == "on"

    hass.bus.async_fire(EVENT_TAG_SCANNED, {"tag_id": "tag-uuid-1"})
    await hass.async_block_till_done()

    assert entry.subentries[subentry_id].data["last_performed"].startswith(days_ago(0))
    assert hass.states.get("binary_sensor.descale_kettle").state == "off"
