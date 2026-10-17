"""Tests for setting up and removing the integration."""

import re
from pathlib import Path

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.home_maintenance.const import DOMAIN, VERSION

PANEL_CONST = (
    Path(__file__).parent.parent
    / "custom_components/home_maintenance/panel/src/const.ts"
)


async def test_unload_and_remove_entry(
    hass: HomeAssistant, setup_integration, caplog: pytest.LogCaptureFixture
) -> None:
    """Removing the entry cleans up without errors."""
    entry = setup_integration
    assert entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert DOMAIN not in hass.data
    assert "Error" not in caplog.text


async def test_invalid_last_performed_is_rejected(
    hass: HomeAssistant, setup_integration, hass_ws_client
) -> None:
    """A task with an unparsable date is refused."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "home_maintenance/add_task",
            "title": "Bad date",
            "interval_value": 1,
            "interval_type": "days",
            "last_performed": "not a date",
        }
    )
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "invalid_date"


def test_panel_version_matches() -> None:
    """The panel shows the same version as the integration."""
    match = re.search(r"VERSION = '([^']+)'", PANEL_CONST.read_text())
    assert match
    assert match.group(1) == VERSION
