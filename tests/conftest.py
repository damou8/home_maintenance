"""Fixtures and helpers for Home Maintenance tests."""

from datetime import timedelta
from typing import Any

import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.home_maintenance.const import DOMAIN

DEFAULT_OPTIONS = {
    "notify_targets": ["notify.phone_a", "notify.phone_b"],
    "notify_time": "09:00:00",
    "notify_days_before": 1,
    "notify_overdue": True,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in all tests."""


def days_ago(days: int) -> str:
    """Return the local date `days` days ago, as a date field gives it."""
    return (dt_util.now().date() - timedelta(days=days)).isoformat()


@pytest.fixture
def options() -> dict[str, Any]:
    """Options of the config entry, override in a test module if needed."""
    return dict(DEFAULT_OPTIONS)


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, options: dict[str, Any]
) -> MockConfigEntry:
    """Set up the integration with a config entry and no tasks."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home Maintenance",
        data={},
        options=options,
        version=2,
        minor_version=1,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def add_task(
    hass: HomeAssistant,
    entry: ConfigEntry,
    title: str,
    interval_days: int | None = 7,
    done_days_ago: int = 0,
    **fields: Any,
) -> str:
    """Add a task through the Add task flow, return its subentry ID."""
    # With interval_days None the task has no interval: the form sends no value
    data = {
        "title": title,
        "interval_value": interval_days,
        "interval_type": "days",
        "last_performed": days_ago(done_days_ago),
        "runtime": {},
        "notifications": {"notify_mode": "default"},
        **fields,
    }
    if interval_days is None:
        del data["interval_value"]
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "task"), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], data
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    await hass.async_block_till_done()
    return next(s.subentry_id for s in entry.subentries.values() if s.title == title)


async def update_task(
    hass: HomeAssistant, entry: ConfigEntry, subentry_id: str, **data: Any
) -> None:
    """Change some of a task's data directly."""
    subentry = entry.subentries[subentry_id]
    hass.config_entries.async_update_subentry(
        entry, subentry, data={**subentry.data, **data}
    )
    await hass.async_block_till_done()
