"""Count the hours an entity is on, for tasks with a runtime limit."""

import math
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import CONF_RUNTIME_ENTITY, CONF_RUNTIME_HOURS, DOMAIN
from .tasks import has_runtime, iter_tasks, task_id

STORAGE_KEY = f"{DOMAIN}.runtime"
STORAGE_VERSION = 1

# While an entity is on: refresh its tasks' entities and check the notification
# thresholds every minute, save the counters every 10 minutes
UPDATE_INTERVAL = timedelta(minutes=1)
SAVE_INTERVAL = timedelta(minutes=10)

NOT_ON_STATES = {STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN}

# Repair issue raised for a task whose counted entity was removed or renamed
ISSUE_MISSING_ENTITY = "missing_runtime_entity"

# Called with the task, its previous and its new remaining percentage
type RemainingChangedCallback = Callable[[ConfigSubentry, float, float], None]


def is_on(state: State | None) -> bool:
    """Return whether an entity counts as on: in any state but off."""
    return state is not None and state.state not in NOT_ON_STATES


def round_up(value: float, decimals: int = 0) -> float:
    """Round up to some decimals, so a value only reads 0 once it is 0."""
    # Float noise is rounded off first: 500 * 32.2 / 100 is 161.00000000000003,
    # which would otherwise round up to 162
    factor = 10**decimals
    return math.ceil(round(value * factor, 6)) / factor


# The hours are state, not configuration, so they're kept in their own storage
# file rather than in the task: saving a task writes the config entries file and
# fires the entry's update listener.
class RuntimeTracker:
    """Hours each task's entity was on since the task was last done."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        on_remaining_changed: RemainingChangedCallback,
    ) -> None:
        """Initialize the tracker."""
        self.hass = hass
        self.entry = entry
        self._on_remaining_changed = on_remaining_changed
        self._store: Store[dict[str, float]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        # Subentry ID of each task with a runtime limit, by task ID
        self._tasks: dict[str, str] = {}
        # Task IDs by the entity they count
        self._entity_tasks: dict[str, list[str]] = {}
        # Seconds used by task ID, without the session going on
        self._used: dict[str, float] = {}
        # When the session going on started, for the tasks whose entity is on
        self._on_since: dict[str, datetime] = {}
        # Remaining percentage last seen, to notice a threshold being crossed
        self._last_remaining: dict[str, float] = {}
        self._listeners: dict[str, list[CALLBACK_TYPE]] = {}
        # Counted entities that were found missing, with a repair issue raised
        self._missing: set[str] = set()
        self._unsubs: list[CALLBACK_TYPE] = []
        self._unsub_timer: CALLBACK_TYPE | None = None
        self._last_save = dt_util.utcnow()

    async def async_load(self) -> None:
        """Load the saved counters of the tasks that have a runtime limit."""
        stored = await self._store.async_load() or {}
        for subentry in iter_tasks(self.entry):
            if not has_runtime(subentry.data):
                continue
            tid = task_id(subentry)
            self._tasks[tid] = subentry.subentry_id
            self._entity_tasks.setdefault(
                subentry.data[CONF_RUNTIME_ENTITY], []
            ).append(tid)
            # Counters of removed tasks, or of tasks no longer limited, are dropped
            self._used[tid] = float(stored.get(tid, 0))

    @callback
    def async_start(self) -> None:
        """Start counting, from now for the entities that are already on."""
        now = dt_util.utcnow()
        for entity_id, tids in self._entity_tasks.items():
            if is_on(self.hass.states.get(entity_id)):
                for tid in tids:
                    self._on_since[tid] = now
        for tid in self._tasks:
            self._last_remaining[tid] = self.remaining(tid)

        if self._entity_tasks:
            entity_ids = list(self._entity_tasks)
            self._unsubs += [
                async_track_state_change_event(
                    self.hass, entity_ids, self._async_state_changed
                ),
                async_track_entity_registry_updated_event(
                    self.hass, entity_ids, self._async_registry_updated
                ),
            ]
        # Once every integration is set up, so their entities exist
        self._unsubs.append(async_at_started(self.hass, self._async_check_entities))
        async_delete_missing_entity_issues(self.hass, keep=self._tasks)
        # Config entries aren't unloaded when Home Assistant stops: save then.
        # Not async_listen_once, whose remover fails once the event fired
        self._unsubs.append(
            self.hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, self._async_on_stop)
        )
        self._async_update_timer()

    async def async_unload(self) -> None:
        """Stop counting and save the counters."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        await self._store.async_save(self._data_to_save())

    def has_task(self, tid: str) -> bool:
        """Return whether a task's runtime is counted."""
        return tid in self._tasks

    def used_hours(self, tid: str) -> float:
        """Return the hours a task's entity was on since the task was done."""
        used = self._used.get(tid, 0.0)
        if (since := self._on_since.get(tid)) is not None:
            used += (dt_util.utcnow() - since).total_seconds()
        return used / 3600

    def _limit(self, tid: str) -> int:
        return self.entry.subentries[self._tasks[tid]].data[CONF_RUNTIME_HOURS]

    def hours_left(self, tid: str) -> float:
        """Return the hours of runtime left before a task is due."""
        return max(0.0, self._limit(tid) - self.used_hours(tid))

    def remaining(self, tid: str) -> float:
        """Return the percentage of a task's runtime limit that is left."""
        # Rounded so float noise doesn't keep 30.000000000000004 above a 30% threshold
        return round(100 * self.hours_left(tid) / self._limit(tid), 6)

    @callback
    def async_set_used(self, tid: str, hours: float) -> None:
        """Set the hours a task has used: 0 when it's done, or a correction."""
        self._used[tid] = hours * 3600
        if tid in self._on_since:
            self._on_since[tid] = dt_util.utcnow()
        if tid in self._tasks:
            # A reset or a correction isn't a threshold being crossed
            self._last_remaining[tid] = self.remaining(tid)
            self._async_update_listeners(tid)
        self._async_schedule_save()

    @callback
    def async_add_listener(self, tid: str, update: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Call `update` when a task's runtime changes, return the remover."""
        listeners = self._listeners.setdefault(tid, [])
        listeners.append(update)
        return lambda: listeners.remove(update)

    @callback
    def _async_state_changed(self, event: Event[EventStateChangedData]) -> None:
        """Start or end the sessions of the tasks counting this entity."""
        entity_id = event.data["entity_id"]
        if entity_id in self._missing and event.data["new_state"] is not None:
            self._async_set_missing(entity_id, missing=False)
        now = dt_util.utcnow()
        on = is_on(event.data["new_state"])
        changed = False
        for tid in self._entity_tasks.get(entity_id, []):
            if on and tid not in self._on_since:
                self._on_since[tid] = now
            elif not on and (since := self._on_since.pop(tid, None)) is not None:
                self._used[tid] += (now - since).total_seconds()
                self._async_task_updated(tid)
            else:
                continue
            changed = True
        if changed:
            self._async_update_timer()
            self._async_schedule_save()

    @callback
    def _async_tick(self, _now: datetime) -> None:
        """Update the tasks whose entity is on."""
        for tid in list(self._on_since):
            self._async_task_updated(tid)
        if dt_util.utcnow() - self._last_save >= SAVE_INTERVAL:
            self._async_schedule_save()

    @callback
    def _async_task_updated(self, tid: str) -> None:
        """Report a task's new remaining percentage."""
        remaining = self.remaining(tid)
        previous = self._last_remaining.get(tid, remaining)
        self._last_remaining[tid] = remaining
        if remaining != previous:
            subentry = self.entry.subentries[self._tasks[tid]]
            self._on_remaining_changed(subentry, previous, remaining)
        self._async_update_listeners(tid)

    @callback
    def _async_update_listeners(self, tid: str) -> None:
        for update in list(self._listeners.get(tid, [])):
            update()

    @callback
    def _async_update_timer(self) -> None:
        """Run the timer only while an entity is on."""
        if self._on_since and self._unsub_timer is None:
            self._unsub_timer = async_track_time_interval(
                self.hass, self._async_tick, UPDATE_INTERVAL
            )
        elif not self._on_since and self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def _async_check_entities(self, _hass: HomeAssistant) -> None:
        """Raise or clear the repair issue of each counted entity."""
        ent_reg = er.async_get(self.hass)
        for entity_id in self._entity_tasks:
            exists = (
                self.hass.states.get(entity_id) is not None
                or ent_reg.async_get(entity_id) is not None
            )
            self._async_set_missing(entity_id, missing=not exists)

    @callback
    def _async_registry_updated(
        self, event: Event[er.EventEntityRegistryUpdatedData]
    ) -> None:
        """Notice a counted entity being removed, renamed or created."""
        data = event.data
        if data["action"] == "create":
            self._async_set_missing(data["entity_id"], missing=False)
        elif data["action"] == "remove":
            self._async_set_missing(data["entity_id"], missing=True)
        # Renamed: the event is dispatched under the old ID, the one counted
        elif (old_entity_id := data.get("old_entity_id")) is not None:
            self._async_set_missing(old_entity_id, missing=True)

    @callback
    def _async_set_missing(self, entity_id: str, *, missing: bool) -> None:
        """Raise or clear the repair issue of the tasks counting an entity."""
        if missing:
            self._missing.add(entity_id)
        else:
            self._missing.discard(entity_id)
        for tid in self._entity_tasks.get(entity_id, []):
            issue_id = f"{ISSUE_MISSING_ENTITY}_{tid}"
            if not missing:
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)
                continue
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_MISSING_ENTITY,
                translation_placeholders={
                    "task": self.entry.subentries[self._tasks[tid]].title,
                    "entity_id": entity_id,
                },
            )

    @callback
    def _async_on_stop(self, _event: Event) -> None:
        # While stopping, a delayed save is written at the final write
        self._async_schedule_save()

    @callback
    def _async_schedule_save(self) -> None:
        self._last_save = dt_util.utcnow()
        self._store.async_delay_save(self._data_to_save)

    def _data_to_save(self) -> dict[str, float]:
        """Return the seconds used by each task, sessions going on included."""
        return {tid: self.used_hours(tid) * 3600 for tid in self._used}


@callback
def async_delete_missing_entity_issues(
    hass: HomeAssistant, keep: Iterable[str] = ()
) -> None:
    """Delete the repair issues of tasks no longer counted, all but `keep`."""
    kept = {f"{ISSUE_MISSING_ENTITY}_{tid}" for tid in keep}
    for domain, issue_id in list(ir.async_get(hass).issues):
        if (
            domain == DOMAIN
            and issue_id.startswith(ISSUE_MISSING_ENTITY)
            and issue_id not in kept
        ):
            ir.async_delete_issue(hass, DOMAIN, issue_id)


async def async_remove_runtime_data(hass: HomeAssistant) -> None:
    """Delete the saved counters and repair issues, when the integration is removed."""
    async_delete_missing_entity_issues(hass)
    await Store(hass, STORAGE_VERSION, STORAGE_KEY).async_remove()
