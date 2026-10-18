# Spec: runtime-based tasks (2.1.0)

Implements [the confirmed intent](../intent/runtime-tasks.md).

## Task data

New optional keys in a task subentry's `data`. Existing tasks don't have them and keep working unchanged.

| Key | Type | Meaning |
| --- | --- | --- |
| `runtime_entity` | entity ID or `None` | The task has a runtime limit when set. Runtime counts while this entity's state is anything but `off`, `unavailable` or `unknown`. |
| `runtime_hours` | int or `None` | Lifespan in hours of runtime. Required when `runtime_entity` is set. |
| `notify_runtime_threshold` | int (%) or `None` | Per-task override of the preventive warning. `None` uses the integration's default. `0` disables it. |

`interval_value` becomes optional: `None` means no calendar limit. A task needs an interval, a runtime limit or both.

No config entry version bump: nothing is renamed and every new key is read with `.get()`.

## Runtime counter

The hours used are state, not configuration, so they aren't stored in the subentry. Storing them there would write the config entries file and fire the update listener every minute. They live in `runtime.py`:

- **`RuntimeTracker`**: one per config entry, held in `runtime_data.runtime`.
  - Persisted in `.storage/home_maintenance.runtime` as `{task_id: seconds_used}`.
  - Saved on every on/off change, every 10 minutes while something is on, when HA stops and when the entry unloads. A crash loses at most 10 minutes.
  - Counts only while HA runs. After a restart, a session starts again if the entity is on.
  - Listens to the state changes of every task's runtime entity. While at least one is on, a 1-minute timer refreshes the task's entities and checks the notification thresholds.
- **Marking done** (button, action, NFC tag) resets the counter to 0, through `async_mark_done()`. This also works when the task is marked done twice on the same day.
- **Hours already used**: the add form takes the current usage of an item that isn't new. The change form shows the hours counted so far, and changing that number corrects the counter.
- **Removed tasks** lose their counter at the next setup. Removing the integration deletes the file.

`remaining = max(0, 100 × (1 − used / runtime_hours))`.

## Form

The add and change task forms get:

- "Every" becomes optional.
- A new **Runtime limit** section, collapsed unless the task has one:
  - Entity ("Count while on"), any domain.
  - Lifespan (hours).
  - Hours already used (hours, decimal).
- In the Notifications section: **Runtime warning (% left)**, left blank to use the default.

Errors:

- Neither an interval nor a runtime entity: *Set an interval, a runtime limit or both.*
- A runtime entity without a lifespan: *Enter the lifespan in hours.*

The lifespan is ignored when the entity is cleared, so clearing the entity removes the runtime limit.

**Options:** a new **Runtime warning (% left)** field, 0–100, default 10, where 0 disables the warning.

## Entities

| Entity | Created when | State |
| --- | --- | --- |
| Due `binary_sensor` | always | `on` when enabled and due by date **or** at 0% runtime. A task with no interval is never due by date. |
| Mark done `button` | always | unchanged |
| Last done `sensor` | always | unchanged |
| Next due `sensor` | always | unchanged; unknown for a task without an interval |
| **Interval `sensor`** (new) | the task has an interval | the interval as text in HA's language, such as `3 months` or `3 mois`. Home Assistant only takes translated units from English, so the unit is in the state rather than a unit of measurement. |
| **Remaining `sensor`** (new) | the task has a runtime limit | `%` left, 1 decimal, shown without decimals. Attributes `hours_used` and `hours_limit`. |
| **Hours left `sensor`** (new) | the task has a runtime limit | hours left (duration), 1 decimal, rounded up |
| **Lifespan `sensor`** (new) | the task has a runtime limit | the runtime limit in hours (duration) |

The due binary sensor gets new attributes, which the card reads:

- `runtime_entity`
- `runtime_limit`
- `runtime_remaining`: %, rounded up
- `runtime_left`: hours, rounded up

Both are rounded up so they only show 0 when the limit is reached. A limit's sensors are removed from the entity registry when the limit is removed: Interval with the interval, the runtime sensors with the runtime limit.

## Notifications

- **Preventive (runtime):** sent once, as soon as the remaining percentage drops below the task's threshold, to the task's targets. The tracker compares each new value with the previous one, so a restart or a threshold change doesn't send it again.
- **0% (runtime):** sent as soon as it's reached. The daily run at the notify time repeats it every morning until the task is marked done.
- **Dates:** unchanged. A task due by runtime gets the runtime message in the daily run instead of the date one, so it gets one notification per morning.
- Disabled tasks and tasks with notifications set to none send nothing. The counter still runs, but a disabled task is never due.

## Card

The second line depends on the task's limits:

| Task | Second line |
| --- | --- |
| Date only | `Next: {date} ({pct}%)`, unchanged |
| Hours only | `{pct}% left ({hours} h)` |
| Hybrid | `Next: {date} · {pct}% left`, where the percentage is the runtime one |

The color turns blue when either the date or the runtime percentage is under the card's threshold. All strings are in en, fr and de.

## Tests

- Add form validation: no limit, entity without a lifespan, hours-only and hybrid tasks.
- Counting:
  - `on`/`cool` count.
  - `off`, `unavailable` and `unknown` don't.
  - The Remaining sensor and the due sensor follow the count.
- Mark done resets the counter, also on the same day.
- Persistence across a reload and across a restart (stored file).
- Hours already used, on the add form and the change form.
- Notifications:
  - Preventive fires once at the crossing.
  - 0% fires at the crossing, then in the daily run.
  - The per-task threshold override.
  - Disabled tasks send nothing.
- Entity cleanup when the runtime limit or the interval is removed.
