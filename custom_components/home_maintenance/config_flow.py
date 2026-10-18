"""Config flow for Home Maintenance: the integration, its options and its tasks."""

import uuid
from collections.abc import Mapping
from typing import Any

import probatio as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentry,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    BooleanSelector,
    DateSelector,
    EntitySelector,
    EntitySelectorConfig,
    IconSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TimeSelector,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ENABLED,
    CONF_ICON,
    CONF_INTERVAL_TYPE,
    CONF_INTERVAL_VALUE,
    CONF_LAST_PERFORMED,
    CONF_NOTIFY_DAYS_BEFORE,
    CONF_NOTIFY_MODE,
    CONF_NOTIFY_OVERDUE,
    CONF_NOTIFY_TARGETS,
    CONF_NOTIFY_TIME,
    CONF_TAG_ID,
    DEFAULT_NOTIFY_DAYS_BEFORE,
    DEFAULT_NOTIFY_OVERDUE,
    DEFAULT_NOTIFY_TIME,
    DOMAIN,
    INTERVAL_TYPES,
    NAME,
    NOTIFY_MODE_CUSTOM,
    NOTIFY_MODE_DEFAULT,
    NOTIFY_MODES,
    SUBENTRY_TASK,
)
from .tasks import start_of_day_iso

CONF_TITLE = "title"
SECTION_NOTIFICATIONS = "notifications"

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NOTIFY_TARGETS): EntitySelector(
            EntitySelectorConfig(domain="notify", multiple=True)
        ),
        vol.Required(CONF_NOTIFY_TIME, default=DEFAULT_NOTIFY_TIME): TimeSelector(),
        vol.Required(
            CONF_NOTIFY_DAYS_BEFORE, default=DEFAULT_NOTIFY_DAYS_BEFORE
        ): NumberSelector(
            NumberSelectorConfig(min=0, max=30, mode=NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_NOTIFY_OVERDUE, default=DEFAULT_NOTIFY_OVERDUE
        ): BooleanSelector(),
    }
)


def _task_schema(*, reconfigure: bool) -> vol.Schema:
    """Return the form of a task."""
    # A new task was done today unless told otherwise; an existing one has a date
    last_performed = vol.Required if reconfigure else vol.Optional
    schema: dict[Any, Any] = {
        vol.Required(CONF_TITLE): TextSelector(),
        vol.Required(CONF_INTERVAL_VALUE): NumberSelector(
            NumberSelectorConfig(min=1, step=1, mode=NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_INTERVAL_TYPE, default="days"): SelectSelector(
            SelectSelectorConfig(
                options=INTERVAL_TYPES,
                translation_key=CONF_INTERVAL_TYPE,
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
        last_performed(CONF_LAST_PERFORMED): DateSelector(),
        vol.Optional(CONF_ICON): IconSelector(),
        vol.Optional(CONF_TAG_ID): EntitySelector(EntitySelectorConfig(domain="tag")),
    }
    if reconfigure:
        schema[vol.Required(CONF_ENABLED, default=True)] = BooleanSelector()
    schema[vol.Required(SECTION_NOTIFICATIONS)] = section(
        vol.Schema(
            {
                vol.Required(
                    CONF_NOTIFY_MODE, default=NOTIFY_MODE_DEFAULT
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=NOTIFY_MODES,
                        translation_key=CONF_NOTIFY_MODE,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_NOTIFY_TARGETS): EntitySelector(
                    EntitySelectorConfig(domain="notify", multiple=True)
                ),
            }
        ),
        {"collapsed": True},
    )
    return vol.Schema(schema)


def _form_values(subentry: ConfigSubentry) -> dict[str, Any]:
    """Return the form values of an existing task."""
    task = subentry.data
    values = {
        CONF_TITLE: subentry.title,
        CONF_INTERVAL_VALUE: task[CONF_INTERVAL_VALUE],
        CONF_INTERVAL_TYPE: task[CONF_INTERVAL_TYPE],
        # Stored as local midnight, so the date part is the local date
        CONF_LAST_PERFORMED: task[CONF_LAST_PERFORMED][:10],
        CONF_ENABLED: task.get(CONF_ENABLED, True),
        SECTION_NOTIFICATIONS: {
            CONF_NOTIFY_MODE: task.get(CONF_NOTIFY_MODE, NOTIFY_MODE_DEFAULT),
            CONF_NOTIFY_TARGETS: task.get(CONF_NOTIFY_TARGETS) or [],
        },
    }
    for key in (CONF_ICON, CONF_TAG_ID):
        if task.get(key):
            values[key] = task[key]
    return values


def _parse_task_input(
    user_input: Mapping[str, Any],
) -> tuple[str, dict[str, Any], dict[str, str]]:
    """Return the title, data and errors of a submitted task form."""
    errors: dict[str, str] = {}
    title = user_input[CONF_TITLE].strip()
    if not title:
        errors[CONF_TITLE] = "empty_title"

    notifications = user_input.get(SECTION_NOTIFICATIONS, {})
    notify_mode = notifications.get(CONF_NOTIFY_MODE, NOTIFY_MODE_DEFAULT)
    notify_targets = notifications.get(CONF_NOTIFY_TARGETS) or []
    if notify_mode != NOTIFY_MODE_CUSTOM:
        notify_targets = []
    elif not notify_targets:
        errors["base"] = "no_notify_targets"

    last_performed = user_input.get(CONF_LAST_PERFORMED)
    data = {
        CONF_INTERVAL_VALUE: int(user_input[CONF_INTERVAL_VALUE]),
        CONF_INTERVAL_TYPE: user_input[CONF_INTERVAL_TYPE],
        CONF_LAST_PERFORMED: start_of_day_iso(
            dt_util.parse_date(last_performed) if last_performed else None
        ),
        CONF_ICON: user_input.get(CONF_ICON) or None,
        CONF_TAG_ID: user_input.get(CONF_TAG_ID) or None,
        CONF_ENABLED: user_input.get(CONF_ENABLED, True),
        CONF_NOTIFY_MODE: notify_mode,
        CONF_NOTIFY_TARGETS: notify_targets,
    }
    return title, data, errors


class HomeMaintenanceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Home Maintenance."""

    VERSION = 2
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding the integration."""
        if user_input is not None:
            return self.async_create_entry(title=NAME, data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:  # noqa: ARG004
        """Return the options flow."""
        return HomeMaintenanceOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls,
        config_entry: ConfigEntry,  # noqa: ARG003
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return the subentry types: tasks."""
        return {SUBENTRY_TASK: TaskSubentryFlow}


class HomeMaintenanceOptionsFlow(OptionsFlow):
    """Notification defaults; saving them reloads the integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )


class TaskSubentryFlow(ConfigSubentryFlow):
    """Add or change a task."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a task."""
        errors: dict[str, str] = {}
        if user_input is not None:
            title, data, errors = _parse_task_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title=title, data=data, unique_id=f"{DOMAIN}_{uuid.uuid4().hex}"
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _task_schema(reconfigure=False), user_input
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change a task."""
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}
        if user_input is not None:
            title, data, errors = _parse_task_input(user_input)
            if not errors:
                # The entry's update listener applies the change
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=title,
                    data=data,
                    reason="task_updated",
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _task_schema(reconfigure=True), user_input or _form_values(subentry)
            ),
            errors=errors,
        )
