"""Tests for adding the integration, its options and the task forms."""

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr

from custom_components.home_maintenance.const import DOMAIN

from .conftest import add_task, days_ago


async def test_add_integration(hass: HomeAssistant) -> None:
    """The integration is added after a confirmation, only once."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home Maintenance"
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow(hass: HomeAssistant, setup_integration) -> None:
    """The Configure dialog saves the notification defaults."""
    entry = setup_integration
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
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


async def test_add_task(hass: HomeAssistant, setup_integration) -> None:
    """A new task is a device with a due sensor and a Mark done button."""
    entry = setup_integration
    subentry_id = await add_task(
        hass, entry, "Clean filter", 7, 10, icon="mdi:air-filter"
    )

    subentry = entry.subentries[subentry_id]
    assert subentry.data["interval_value"] == 7
    assert subentry.data["notify_mode"] == "default"

    state = hass.states.get("binary_sensor.clean_filter")
    assert state.state == "on"
    assert state.attributes["icon"] == "mdi:air-filter"
    assert state.attributes["friendly_name"] == "Clean filter"
    assert hass.states.get("button.clean_filter_mark_done")
    last_done = hass.states.get("sensor.clean_filter_last_done")
    assert last_done.state == days_ago(10)
    assert last_done.attributes["device_class"] == "date"
    assert hass.states.get("sensor.clean_filter_next_due").state == days_ago(3)
    assert hass.states.get("sensor.clean_filter_interval").state == "7 days"

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, subentry.unique_id), entry.entry_id
    )
    assert device.name == "Clean filter"


async def test_add_task_defaults_to_today(
    hass: HomeAssistant, setup_integration
) -> None:
    """Without a date, a new task was done today."""
    entry = setup_integration
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "task"), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "title": "Water plants",
            "interval_value": 3,
            "interval_type": "days",
            "runtime": {},
            "notifications": {"notify_mode": "default"},
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    subentry = next(iter(entry.subentries.values()))
    assert subentry.data["last_performed"].startswith(days_ago(0))
    assert hass.states.get("binary_sensor.water_plants").state == "off"


async def test_custom_notifications_need_targets(
    hass: HomeAssistant, setup_integration
) -> None:
    """Custom targets without any target is refused."""
    entry = setup_integration
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "task"), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "title": "Car",
            "interval_value": 1,
            "interval_type": "months",
            "runtime": {},
            "notifications": {"notify_mode": "custom"},
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_notify_targets"}


async def test_reconfigure_task(hass: HomeAssistant, setup_integration) -> None:
    """Changing a task updates its entities, including a rename."""
    entry = setup_integration
    subentry_id = await add_task(hass, entry, "Clean filter", 7, 10)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "task"),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry_id},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "title": "Clean air filter",
            "interval_value": 3,
            "interval_type": "months",
            "last_performed": days_ago(10),
            "enabled": False,
            "runtime": {},
            "notifications": {"notify_mode": "none"},
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "task_updated"
    await hass.async_block_till_done()

    subentry = entry.subentries[subentry_id]
    assert subentry.title == "Clean air filter"
    assert subentry.data["enabled"] is False
    assert subentry.data["notify_mode"] == "none"

    # Same entity, renamed with its device
    state = hass.states.get("binary_sensor.clean_filter")
    assert state.state == "off"
    assert state.attributes["interval_value"] == 3
    assert state.attributes["friendly_name"] == "Clean air filter"
    assert hass.states.get("sensor.clean_filter_interval").state == "3 months"
