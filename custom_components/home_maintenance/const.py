"""Constants for the Home Maintenance integration."""

VERSION = "2.0.0"
NAME = "Home Maintenance"

DOMAIN = "home_maintenance"

# Each task is a config subentry of this type
SUBENTRY_TASK = "task"

# Task data, stored in the subentry (its title is the task title)
CONF_INTERVAL_VALUE = "interval_value"
CONF_INTERVAL_TYPE = "interval_type"
CONF_LAST_PERFORMED = "last_performed"
CONF_ICON = "icon"
CONF_TAG_ID = "tag_id"
CONF_ENABLED = "enabled"
CONF_NOTIFY_MODE = "notify_mode"
CONF_NOTIFY_TARGETS = "notify_targets"

INTERVAL_TYPES = ["days", "weeks", "months"]
DEFAULT_ICON = "mdi:calendar-check"

# Per-task notification override
NOTIFY_MODE_DEFAULT = "default"  # use the integration's notify targets
NOTIFY_MODE_CUSTOM = "custom"  # use the task's own notify targets
NOTIFY_MODE_NONE = "none"  # never notify for this task
NOTIFY_MODES = [NOTIFY_MODE_DEFAULT, NOTIFY_MODE_CUSTOM, NOTIFY_MODE_NONE]

# Integration options: notification defaults
CONF_NOTIFY_TIME = "notify_time"
CONF_NOTIFY_DAYS_BEFORE = "notify_days_before"
CONF_NOTIFY_OVERDUE = "notify_overdue"

DEFAULT_NOTIFY_TIME = "09:00:00"
DEFAULT_NOTIFY_DAYS_BEFORE = 1
DEFAULT_NOTIFY_OVERDUE = True

SERVICE_RESET = "reset_last_performed"
SERVICE_SEND_NOTIFICATIONS = "send_notifications"

# Dashboard card, loaded on every frontend page; versioned so updates bypass the cache
STATIC_PATH = "/home_maintenance_static"
CARD_URL = f"{STATIC_PATH}/home-maintenance-card.js?v={VERSION}"
