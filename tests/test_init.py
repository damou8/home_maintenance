"""Tests for setup, removal and migration from 1.x."""

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.home_maintenance.const import DOMAIN

from .conftest import add_task, days_ago


async def test_unload_and_remove_entry(
    hass: HomeAssistant, setup_integration, caplog: pytest.LogCaptureFixture
) -> None:
    """Removing the entry cleans up without errors."""
    entry = setup_integration
    await add_task(hass, entry, "Clean filter")
    assert entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.clean_filter") is None
    assert "Error" not in caplog.text


def v1_task(task_id: str, title: str, **fields) -> dict:
    """Return a task as 1.x stored it."""
    return {
        "id": task_id,
        "title": title,
        "interval_value": 7,
        "interval_type": "days",
        "last_performed": dt_util.start_of_local_day(
            dt_util.parse_date(days_ago(10))
        ).isoformat(),
        "tag_id": None,
        "icon": "mdi:air-filter",
        **fields,
    }


async def test_migrate_from_v1(hass: HomeAssistant, hass_storage) -> None:
    """1.x tasks become subentries and keep their entities."""
    hass_storage["home_maintenance.storage"] = {
        "version": 1,
        "minor_version": 1,
        "key": "home_maintenance.storage",
        "data": [
            # Stored before enabled and notifications existed
            v1_task("home_maintenance_aaa", "Clean filter"),
            v1_task(
                "home_maintenance_bbb",
                "Car service",
                enabled=False,
                notify_mode="custom",
                notify_targets=["notify.phone_c"],
            ),
        ],
    }
    # 1.x stored its version as a string
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home Maintenance",
        data={"admin_only": True, "sidebar_title": "Maintenance"},
        options={
            "admin_only": True,
            "sidebar_title": "Maintenance",
            "notify_targets": ["notify.phone_a"],
            "notify_time": "09:00:00",
        },
        version="1.1.0",
    )
    entry.add_to_hass(hass)

    # 1.x registry: every task entity on one shared device
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    hub = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "home_maintenance_hub")},
        name="Home Maintenance",
    )
    old = ent_reg.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        "home_maintenance_aaa",
        suggested_object_id="home_maintenance_clean_filter",
        config_entry=entry,
        device_id=hub.id,
    )
    ent_reg.async_update_entity(old.entity_id, labels={"chores"})

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.version == 2
    assert entry.data == {}
    assert entry.options == {
        "notify_targets": ["notify.phone_a"],
        "notify_time": "09:00:00",
    }
    assert "home_maintenance.storage" not in hass_storage

    tasks = {s.unique_id: s for s in entry.subentries.values()}
    assert tasks["home_maintenance_aaa"].title == "Clean filter"
    assert tasks["home_maintenance_aaa"].data["enabled"] is True
    assert tasks["home_maintenance_aaa"].data["notify_mode"] == "default"
    assert tasks["home_maintenance_bbb"].data["enabled"] is False
    assert tasks["home_maintenance_bbb"].data["notify_targets"] == ["notify.phone_c"]

    # The entity keeps its ID and labels, on its own device
    reg = ent_reg.async_get("binary_sensor.home_maintenance_clean_filter")
    assert reg.labels == {"chores"}
    assert reg.config_subentry_id == tasks["home_maintenance_aaa"].subentry_id
    device = dev_reg.async_get(reg.device_id)
    assert device.name == "Clean filter"
    assert dev_reg.async_get(hub.id) is None

    state = hass.states.get("binary_sensor.home_maintenance_clean_filter")
    assert state.state == "on"
    assert state.attributes["icon"] == "mdi:air-filter"
    assert state.attributes["friendly_name"] == "Clean filter"
    assert hass.states.get("button.clean_filter_mark_done")
