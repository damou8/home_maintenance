"""Move the tasks of 1.x, kept in their own storage file, into config subentries."""

import logging
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

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
    DOMAIN,
    NOTIFY_MODE_DEFAULT,
    SUBENTRY_TASK,
)

_LOGGER = logging.getLogger(__name__)

V1_STORAGE_KEY = f"{DOMAIN}.storage"
# 1.x put every task entity on this one device
V1_DEVICE_IDENTIFIER = (DOMAIN, "home_maintenance_hub")
# The panel's settings are gone with the panel
OPTIONS_KEPT = (
    CONF_NOTIFY_TARGETS,
    CONF_NOTIFY_TIME,
    CONF_NOTIFY_DAYS_BEFORE,
    CONF_NOTIFY_OVERDUE,
)


async def async_migrate_v1(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Turn each stored task into a subentry, keeping its entity."""
    store: Store[list[dict]] = Store(hass, 1, V1_STORAGE_KEY, minor_version=1)
    tasks = await store.async_load() or []

    ent_reg = er.async_get(hass)
    migrated = {subentry.unique_id for subentry in entry.subentries.values()}
    for task in tasks:
        if task["id"] in migrated:
            continue
        subentry = ConfigSubentry(
            data=MappingProxyType(
                {
                    CONF_INTERVAL_VALUE: int(task[CONF_INTERVAL_VALUE]),
                    CONF_INTERVAL_TYPE: task[CONF_INTERVAL_TYPE],
                    CONF_LAST_PERFORMED: task[CONF_LAST_PERFORMED],
                    CONF_ICON: task.get(CONF_ICON),
                    CONF_TAG_ID: task.get(CONF_TAG_ID),
                    CONF_ENABLED: task.get(CONF_ENABLED, True),
                    CONF_NOTIFY_MODE: task.get(CONF_NOTIFY_MODE, NOTIFY_MODE_DEFAULT),
                    CONF_NOTIFY_TARGETS: task.get(CONF_NOTIFY_TARGETS) or [],
                }
            ),
            subentry_type=SUBENTRY_TASK,
            title=task["title"],
            # Same unique ID as the entity, so it keeps its ID, history and labels
            unique_id=task["id"],
        )
        hass.config_entries.async_add_subentry(entry, subentry)
        if entity_id := ent_reg.async_get_entity_id(
            "binary_sensor", DOMAIN, task["id"]
        ):
            # Detach it from the shared device before that device is removed
            ent_reg.async_update_entity(
                entity_id, config_subentry_id=subentry.subentry_id, device_id=None
            )

    # Each task now has its own device
    dev_reg = dr.async_get(hass)
    if device := dev_reg.async_get_device_by_identifier(
        V1_DEVICE_IDENTIFIER, entry.entry_id
    ):
        dev_reg.async_remove_device(device.id)

    hass.config_entries.async_update_entry(
        entry,
        data={},
        options={
            key: entry.options[key] for key in OPTIONS_KEPT if key in entry.options
        },
        version=2,
        minor_version=1,
    )
    await store.async_remove()
    _LOGGER.info("Moved %d tasks to the integration's configuration", len(tasks))
