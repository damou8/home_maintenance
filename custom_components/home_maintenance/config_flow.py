"""Config flow for Home Maintenance: the integration, its options and its tasks."""

import uuid
from collections.abc import Mapping
from typing import Any

import probatio as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
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
    CONF_NOTIFY_RUNTIME_THRESHOLD,
    CONF_NOTIFY_TARGETS,
    CONF_NOTIFY_TIME,
    CONF_RUNTIME_ENTITY,
    CONF_RUNTIME_HOURS,
    CONF_RUNTIME_USED,
    CONF_TAG_ID,
    DEFAULT_NOTIFY_DAYS_BEFORE,
    DEFAULT_NOTIFY_OVERDUE,
    DEFAULT_NOTIFY_RUNTIME_THRESHOLD,
    DEFAULT_NOTIFY_TIME,
    DOMAIN,
    INTERVAL_TYPES,
    NAME,
    NOTIFY_MODE_CUSTOM,
    NOTIFY_MODE_DEFAULT,
    NOTIFY_MODES,
    SUBENTRY_TASK,
)
from .runtime import RuntimeTracker
from .tasks import start_of_day_iso, task_id

CONF_TITLE = "title"
SECTION_RUNTIME = "runtime"
SECTION_NOTIFICATIONS = "notifications"

PERCENT_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=0, max=100, step=1, unit_of_measurement="%", mode=NumberSelectorMode.BOX
    )
)

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
        vol.Required(
            CONF_NOTIFY_RUNTIME_THRESHOLD, default=DEFAULT_NOTIFY_RUNTIME_THRESHOLD
        ): PERCENT_SELECTOR,
    }
)


def _task_schema(*, reconfigure: bool, runtime: bool = False) -> vol.Schema:
    """Return the form of a task, with its runtime section open if it has one."""
    # A new task was done today unless told otherwise; an existing one has a date
    last_performed = vol.Required if reconfigure else vol.Optional
    hours = NumberSelectorConfig(
        min=0, step=0.1, unit_of_measurement="h", mode=NumberSelectorMode.BOX
    )
    schema: dict[Any, Any] = {
        vol.Required(CONF_TITLE): TextSelector(),
        # Blank for a task that only has a runtime limit
        vol.Optional(CONF_INTERVAL_VALUE): NumberSelector(
            NumberSelectorConfig(min=1, step=1, mode=NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_INTERVAL_TYPE, default="days"): SelectSelector(
            SelectSelectorConfig(
                options=INTERVAL_TYPES,
                translation_key=CONF_INTERVAL_TYPE,
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(SECTION_RUNTIME): section(
            vol.Schema(
                {
                    vol.Optional(CONF_RUNTIME_ENTITY): EntitySelector(),
                    vol.Optional(CONF_RUNTIME_HOURS): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            step=1,
                            unit_of_measurement="h",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(CONF_RUNTIME_USED): NumberSelector(hours),
                }
            ),
            {"collapsed": not runtime},
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
                # Blank for the integration's default
                vol.Optional(CONF_NOTIFY_RUNTIME_THRESHOLD): PERCENT_SELECTOR,
            }
        ),
        {"collapsed": True},
    )
    return vol.Schema(schema)


def _form_values(subentry: ConfigSubentry, used: float | None) -> dict[str, Any]:
    """Return the form values of an existing task, which has used `used` hours."""
    task = subentry.data
    runtime = {
        CONF_RUNTIME_ENTITY: task.get(CONF_RUNTIME_ENTITY),
        CONF_RUNTIME_HOURS: task.get(CONF_RUNTIME_HOURS),
        CONF_RUNTIME_USED: used,
    }
    notifications = {
        CONF_NOTIFY_MODE: task.get(CONF_NOTIFY_MODE, NOTIFY_MODE_DEFAULT),
        CONF_NOTIFY_TARGETS: task.get(CONF_NOTIFY_TARGETS) or [],
        CONF_NOTIFY_RUNTIME_THRESHOLD: task.get(CONF_NOTIFY_RUNTIME_THRESHOLD),
    }
    # Blank fields are left out, so the form shows them empty
    values = {
        CONF_TITLE: subentry.title,
        CONF_INTERVAL_TYPE: task[CONF_INTERVAL_TYPE],
        # Stored as local midnight, so the date part is the local date
        CONF_LAST_PERFORMED: task[CONF_LAST_PERFORMED][:10],
        CONF_ENABLED: task.get(CONF_ENABLED, True),
        SECTION_RUNTIME: {k: v for k, v in runtime.items() if v is not None},
        SECTION_NOTIFICATIONS: {
            k: v for k, v in notifications.items() if v is not None
        },
    }
    for key in (CONF_INTERVAL_VALUE, CONF_ICON, CONF_TAG_ID):
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
    threshold = notifications.get(CONF_NOTIFY_RUNTIME_THRESHOLD)

    # Clearing the entity removes the runtime limit, whatever the hours say
    runtime = user_input.get(SECTION_RUNTIME, {})
    runtime_entity = runtime.get(CONF_RUNTIME_ENTITY) or None
    runtime_hours = runtime.get(CONF_RUNTIME_HOURS) if runtime_entity else None
    if runtime_entity and not runtime_hours:
        errors["base"] = "no_runtime_hours"
    interval_value = user_input.get(CONF_INTERVAL_VALUE)
    if not interval_value and not runtime_entity:
        errors["base"] = "no_limit"

    last_performed = user_input.get(CONF_LAST_PERFORMED)
    data = {
        CONF_INTERVAL_VALUE: int(interval_value) if interval_value else None,
        CONF_INTERVAL_TYPE: user_input[CONF_INTERVAL_TYPE],
        CONF_LAST_PERFORMED: start_of_day_iso(
            dt_util.parse_date(last_performed) if last_performed else None
        ),
        CONF_ICON: user_input.get(CONF_ICON) or None,
        CONF_TAG_ID: user_input.get(CONF_TAG_ID) or None,
        CONF_ENABLED: user_input.get(CONF_ENABLED, True),
        CONF_NOTIFY_MODE: notify_mode,
        CONF_NOTIFY_TARGETS: notify_targets,
        CONF_NOTIFY_RUNTIME_THRESHOLD: int(threshold)
        if threshold is not None
        else None,
        CONF_RUNTIME_ENTITY: runtime_entity,
        CONF_RUNTIME_HOURS: int(runtime_hours) if runtime_hours else None,
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

    # Hours used shown in the change form, to tell whether they were corrected
    _shown_used: float | None = None

    def _runtime(self) -> RuntimeTracker | None:
        """Return the runtime counter, if the integration is loaded."""
        entry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return None
        return entry.runtime_data.runtime

    @callback
    def _async_store_used(
        self, tid: str, data: Mapping[str, Any], user_input: Mapping[str, Any]
    ) -> None:
        """Store the hours used entered in the form, if they changed."""
        used = user_input.get(SECTION_RUNTIME, {}).get(CONF_RUNTIME_USED)
        runtime = self._runtime()
        if (
            runtime
            and data[CONF_RUNTIME_ENTITY]
            and used is not None
            and used != self._shown_used
        ):
            # Kept by the counter: the reload that follows saves and reads it back
            runtime.async_set_used(tid, used)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a task."""
        errors: dict[str, str] = {}
        if user_input is not None:
            title, data, errors = _parse_task_input(user_input)
            if not errors:
                unique_id = f"{DOMAIN}_{uuid.uuid4().hex}"
                self._async_store_used(unique_id, data, user_input)
                return self.async_create_entry(
                    title=title, data=data, unique_id=unique_id
                )
        runtime = bool(
            user_input and user_input[SECTION_RUNTIME].get(CONF_RUNTIME_ENTITY)
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _task_schema(reconfigure=False, runtime=runtime), user_input
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change a task."""
        subentry = self._get_reconfigure_subentry()
        tid = task_id(subentry)
        if (
            user_input is None
            and (runtime := self._runtime())
            and runtime.has_task(tid)
        ):
            self._shown_used = round(runtime.used_hours(tid), 1)
        errors: dict[str, str] = {}
        if user_input is not None:
            title, data, errors = _parse_task_input(user_input)
            if not errors:
                self._async_store_used(tid, data, user_input)
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
                _task_schema(
                    reconfigure=True,
                    runtime=bool(subentry.data.get(CONF_RUNTIME_ENTITY)),
                ),
                user_input or _form_values(subentry, self._shown_used),
            ),
            errors=errors,
        )
