"""Tests for the options flow."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_options_flow(hass: HomeAssistant, setup_integration) -> None:
    """The Configure dialog opens and saves notification settings."""
    entry = setup_integration
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "admin_only": False,
            "sidebar_title": "Maintenance",
            "notify_targets": ["notify.phone_c"],
            "notify_time": "08:30:00",
            "notify_days_before": 2,
            "notify_overdue": False,
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["notify_targets"] == ["notify.phone_c"]
    assert entry.options["notify_time"] == "08:30:00"
    assert entry.options["notify_overdue"] is False
