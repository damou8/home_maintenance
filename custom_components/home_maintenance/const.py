"""Constants for the Home Maintenance integration."""

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TimeSelector,
)

VERSION = "1.6.0"
NAME = "Home Maintenance"
MANUFACTURER = "@TJPoorman"

DOMAIN = "home_maintenance"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PANEL_FILENAME = "panel/main.js"
PANEL_URL = "home-maintenance"
PANEL_API_PATH = "/home_maintenance_static"
PANEL_API_URL = PANEL_API_PATH + "/main.js"
PANEL_TITLE = NAME
PANEL_ICON = "mdi:hammer-wrench"
PANEL_NAME = "home-maintenance-panel"

DEVICE_KEY = "home_maintenance_hub"

SERVICE_RESET = "reset_last_performed"
SERVICE_SEND_NOTIFICATIONS = "send_notifications"
SERVICE_RESET_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("performed_date"): cv.string,
    }
)

CONF_NOTIFY_TARGETS = "notify_targets"
CONF_NOTIFY_TIME = "notify_time"
CONF_NOTIFY_DAYS_BEFORE = "notify_days_before"
CONF_NOTIFY_OVERDUE = "notify_overdue"

DEFAULT_NOTIFY_TIME = "09:00:00"
DEFAULT_NOTIFY_DAYS_BEFORE = 1
DEFAULT_NOTIFY_OVERDUE = True

# Per-task notification override
NOTIFY_MODE_DEFAULT = "default"  # use the integration's notify targets
NOTIFY_MODE_CUSTOM = "custom"  # use the task's own notify targets
NOTIFY_MODE_NONE = "none"  # never notify for this task
NOTIFY_MODES = [NOTIFY_MODE_DEFAULT, NOTIFY_MODE_CUSTOM, NOTIFY_MODE_NONE]

CONFIG_STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("admin_only", default=True): cv.boolean,
        vol.Optional("sidebar_title", default=PANEL_TITLE): cv.string,
    }
)


def get_options_schema(config_entry: ConfigEntry) -> vol.Schema:
    """Return the schema for get options."""
    return vol.Schema(
        {
            vol.Optional(
                "admin_only",
                default=config_entry.options.get(
                    "admin_only", config_entry.data.get("admin_only", True)
                ),
            ): cv.boolean,
            vol.Optional(
                "sidebar_title",
                default=config_entry.options.get(
                    "sidebar_title",
                    config_entry.data.get("sidebar_title", PANEL_TITLE),
                ),
            ): cv.string,
            # suggested_value instead of default so the list can be emptied
            vol.Optional(
                CONF_NOTIFY_TARGETS,
                description={
                    "suggested_value": config_entry.options.get(CONF_NOTIFY_TARGETS, [])
                },
            ): EntitySelector(EntitySelectorConfig(domain="notify", multiple=True)),
            vol.Optional(
                CONF_NOTIFY_TIME,
                default=config_entry.options.get(CONF_NOTIFY_TIME, DEFAULT_NOTIFY_TIME),
            ): TimeSelector(),
            vol.Optional(
                CONF_NOTIFY_DAYS_BEFORE,
                default=config_entry.options.get(
                    CONF_NOTIFY_DAYS_BEFORE, DEFAULT_NOTIFY_DAYS_BEFORE
                ),
            ): NumberSelector(
                NumberSelectorConfig(min=0, max=30, mode=NumberSelectorMode.BOX)
            ),
            vol.Optional(
                CONF_NOTIFY_OVERDUE,
                default=config_entry.options.get(
                    CONF_NOTIFY_OVERDUE, DEFAULT_NOTIFY_OVERDUE
                ),
            ): BooleanSelector(),
        }
    )
