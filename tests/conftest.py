"""Fixtures for Home Maintenance tests."""

from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.home_maintenance.const import DOMAIN

DEFAULT_OPTIONS = {
    "admin_only": True,
    "sidebar_title": "Home Maintenance",
    "notify_targets": ["notify.phone_a", "notify.phone_b"],
    "notify_time": "09:00:00",
    "notify_days_before": 1,
    "notify_overdue": True,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in all tests."""


def days_ago(days: int) -> str:
    """Return an ISO date string for local midnight `days` days ago."""
    today = dt_util.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return (today - timedelta(days=days)).isoformat()


@pytest.fixture
def options() -> dict[str, Any]:
    """Options of the config entry, override in a test module if needed."""
    return dict(DEFAULT_OPTIONS)


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, options: dict[str, Any]
) -> MockConfigEntry:
    """Set up the integration with a config entry."""
    # Real entries carry the config flow's VERSION, which is the string "1.1.0"
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=options, version="1.1.0")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def ws(
    hass: HomeAssistant, hass_ws_client: Callable[..., Awaitable[Any]]
) -> Callable[..., Awaitable[Any]]:
    """Return a helper sending one websocket command and returning its result."""
    client = await hass_ws_client(hass)

    async def send(**msg: Any) -> Any:
        await client.send_json_auto_id(msg)
        response = await client.receive_json()
        assert response["success"], response
        return response["result"]

    return send
