"""Home Maintenance: track recurring tasks."""

import logging
from dataclasses import dataclass, field

import probatio as vol
from homeassistant.components.tag.const import EVENT_TAG_SCANNED
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .card import async_register_card, async_unregister_card
from .const import (
    CONF_LAST_PERFORMED,
    CONF_TAG_ID,
    DOMAIN,
    SERVICE_RESET,
    SERVICE_SEND_NOTIFICATIONS,
)
from .entity import HomeMaintenanceEntity
from .migration import async_migrate_v1
from .notifications import TaskNotifier
from .runtime import RuntimeTracker, async_remove_runtime_data
from .tasks import async_mark_done, iter_tasks

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_RESET_SCHEMA = vol.Schema(
    {
        # One entity, or several when called with a target
        vol.Required("entity_id"): cv.entity_ids,
        vol.Optional("performed_date"): cv.date,
    }
)


@dataclass
class HomeMaintenanceData:
    """Runtime data of the config entry."""

    notifier: TaskNotifier
    runtime: RuntimeTracker
    # Options and tasks as they were at setup, to tell what changed since
    signature: object
    # Entities that show the task's data, updated in place when it's marked done
    entities: list[HomeMaintenanceEntity] = field(default_factory=list)


type HomeMaintenanceConfigEntry = ConfigEntry[HomeMaintenanceData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # noqa: ARG001
    """Set up the actions, shared by all entries."""
    # 1.x stored its entry version as the string "1.1.0", which Home Assistant
    # can't compare with the config flow's integer version: make it 1 to migrate
    for entry in hass.config_entries.async_entries(DOMAIN):
        if isinstance(entry.version, str):
            hass.config_entries.async_update_entry(entry, version=1)

    _async_register_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: HomeMaintenanceConfigEntry
) -> bool:
    """Set up Home Maintenance from a config entry."""
    notifier = TaskNotifier(hass, entry)
    runtime = RuntimeTracker(hass, entry, notifier.async_runtime_changed)
    await runtime.async_load()
    entry.runtime_data = HomeMaintenanceData(
        notifier=notifier, runtime=runtime, signature=_signature(entry)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    runtime.async_start()
    await async_register_card(hass)

    @callback
    def handle_tag_scanned(event: Event) -> None:
        """Mark the tasks linked to the scanned tag as done."""
        tag_uuid = event.data.get("tag_id")
        ent_reg = er.async_get(hass)
        for subentry in list(iter_tasks(entry)):
            tag_entity_id = subentry.data.get(CONF_TAG_ID)
            if not tag_entity_id:
                continue
            tag_entry = ent_reg.async_get(tag_entity_id)
            if tag_entry and tag_entry.unique_id == tag_uuid:
                _LOGGER.debug("Tag %s scanned for %s", tag_uuid, subentry.title)
                async_mark_done(hass, entry, subentry)

    entry.async_on_unload(hass.bus.async_listen(EVENT_TAG_SCANNED, handle_tag_scanned))
    entry.async_on_unload(notifier.async_start())
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: HomeMaintenanceConfigEntry
) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.runtime.async_unload()
    async_unregister_card(hass)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:  # noqa: ARG001
    """Delete the runtime counters and issues when the integration is removed."""
    await async_remove_runtime_data(hass)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an entry made by an older version."""
    if entry.version == 1:
        await async_migrate_v1(hass, entry)
    return True


def _signature(entry: ConfigEntry) -> object:
    """Return what needs a reload when it changes: all but the last done dates."""
    return (
        dict(entry.options),
        {
            subentry.subentry_id: (
                subentry.title,
                {k: v for k, v in subentry.data.items() if k != CONF_LAST_PERFORMED},
            )
            for subentry in iter_tasks(entry)
        },
    )


async def _async_entry_updated(
    hass: HomeAssistant, entry: HomeMaintenanceConfigEntry
) -> None:
    """Apply changes to the options or the tasks."""
    if _signature(entry) != entry.runtime_data.signature:
        hass.config_entries.async_schedule_reload(entry.entry_id)
        return
    # Only tasks marked done: update them without reloading everything
    for entity in entry.runtime_data.entities:
        entity.async_task_updated()


def _task_for_entity(
    hass: HomeAssistant, entity_id: str
) -> tuple[ConfigEntry, ConfigSubentry]:
    """Return the entry and the task an entity belongs to."""
    reg_entry = er.async_get(hass).async_get(entity_id)
    if reg_entry and reg_entry.platform == DOMAIN and reg_entry.config_subentry_id:
        entry = hass.config_entries.async_get_entry(reg_entry.config_entry_id or "")
        if entry and reg_entry.config_subentry_id in entry.subentries:
            return entry, entry.subentries[reg_entry.config_subentry_id]
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="not_a_task",
        translation_placeholders={"entity_id": entity_id},
    )


@callback
def _async_register_services(hass: HomeAssistant) -> None:
    """Register the integration's actions."""

    async def async_reset(call: ServiceCall) -> None:
        for entity_id in call.data["entity_id"]:
            entry, subentry = _task_for_entity(hass, entity_id)
            async_mark_done(hass, entry, subentry, call.data.get("performed_date"))

    hass.services.async_register(
        DOMAIN, SERVICE_RESET, async_reset, schema=SERVICE_RESET_SCHEMA
    )

    async def async_send_notifications(call: ServiceCall) -> None:  # noqa: ARG001
        for entry in hass.config_entries.async_loaded_entries(DOMAIN):
            await entry.runtime_data.notifier.async_send_notifications()

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_NOTIFICATIONS, async_send_notifications
    )
