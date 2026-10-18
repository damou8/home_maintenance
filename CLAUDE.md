# Home Maintenance

Home Assistant custom integration (domain `home_maintenance`), installed through HACS. It tracks recurring tasks. Each task is a config subentry, managed from the integration's page with HA's own forms. A task is due after a calendar interval, a runtime limit (hours while an entity is on), or whichever comes first. It's shown as a device with a `binary_sensor` that turns `on` when the task is due, date `sensor`s (last done, next due), an Interval `sensor` for a calendar interval, Remaining, Hours left and Lifespan `sensor`s for a runtime limit, and a "Mark done" `button`. The integration also has a dashboard card and sends daily notifications for due tasks.

Fork of TJPoorman/home_maintenance, maintained at github.com/damou8/home_maintenance. Minimum Home Assistant version: 2026.9 (`hacs.json`), the first release that uses `probatio` instead of `voluptuous`.

## Layout

```
custom_components/home_maintenance/
  __init__.py        setup/unload, actions, NFC tag listener, update listener
  config_flow.py     setup, options (notification defaults), TaskSubentryFlow (add/change a task)
  tasks.py           task helpers: compute_next_due() (the only due-date calculation), async_mark_done()
  runtime.py         RuntimeTracker: hours each runtime entity was on, saved in .storage/home_maintenance.runtime
  entity.py          base entity: one device per task
  binary_sensor.py   on when the task is due
  sensor.py          last done and next due dates; interval; runtime left (%, hours) and lifespan
  button.py          Mark done
  notifications.py   TaskNotifier: daily notify.send_message, runtime warnings as they happen; messages in en/fr/de
  migration.py       1.x storage file -> subentries (config entry version 1 -> 2)
  card.py            serves the card and loads it on every page (frontend.add_extra_js_url)
  translations/      every UI string of the integration (en, fr, de)
  frontend/          the dashboard card: TypeScript (Lit + esbuild)
    src/             card, its editor and its own strings (en/fr/de)
    dist/            built bundle, committed: it ships in the release zip
tests/               pytest with pytest-homeassistant-custom-component
```

### How a task is stored and updated

- A task is a `ConfigSubentry` of type `task`. Its title is the task title. Its `data` holds the interval (`interval_value` is `None` for a task with only a runtime limit), the runtime limit (`runtime_entity`, `runtime_hours`), `last_performed` (local midnight, ISO), icon, tag, `enabled` and the notification override. Its `unique_id` is the task ID used in the entities' unique IDs.
- The hours used aren't in the subentry: they change every minute, and saving a subentry writes the config entries file and fires the update listener. `RuntimeTracker` keeps them in its own `Store`, saved on every on/off change, every 10 minutes while counting, when HA stops and when the entry unloads. `async_mark_done()` resets them, and the task forms can correct them. `docs/specs/runtime-tasks.md` has the full design.
- Every change to a subentry or to the options fires the entry's update listener (`_async_entry_updated`). It compares a signature of the options and tasks, leaving out `last_performed`:
  - Anything else changed (task added, changed or deleted, options saved): the entry reloads.
  - Only `last_performed` changed (a task was marked done): the entities in `runtime_data.entities` update in place (`async_task_updated`), without a reload.

## Commands

```bash
# Python tests (CI: Tests). Use their own venv: they pin a newer HA than requirements.txt
python -m pip install -r requirements_test.txt
python -m pytest -q

# Python lint (CI: Lint). ruff comes from requirements.txt (scripts/setup)
ruff check . && ruff format --check .     # scripts/lint fixes instead of checking

# Dashboard card (CI: Frontend)
cd custom_components/home_maintenance/frontend
npm ci
npm run typecheck
npm run build                             # then commit dist/ with the sources

# A throwaway HA on port 8123 with this integration linked in
scripts/setup && scripts/develop
```

## Good practices

- **Keep CI green.** The Lint, Tests, Frontend and Validate (hassfest and HACS) workflows run on every PR. Frontend fails when `dist/` doesn't match the sources. `main` is protected: changes go through a PR, which merges only when these checks pass.
- **Keep workflow actions current by hand.** There's no Dependabot. Actions use floating major tags (`actions/checkout@v7`), and the hassfest and HACS validators follow `master`/`main`, as their docs recommend. Move to a new major version when GitHub warns about a deprecated runtime.
- **Test behaviour changes.** Add a pytest for each bug fix and new feature, and drive the integration the way users do: the task forms (`add_task()` in `tests/conftest.py` goes through the real flow), actions, buttons, the options flow.
- **Stay backward compatible with stored tasks.** Read a new task field with `.get()` and a default, since existing subentries don't have it. Add it to the task form in `config_flow.py` (`_task_schema`, `_form_values`, `_parse_task_input`) and to the translations. A change in the stored format needs a new config entry version and a step in `async_migrate_entry`, with a test.
- **Keep one source of truth.** Due dates come from `compute_next_due()`, runtime from `RuntimeTracker` (`remaining()`, `hours_left()`), and marking done goes through `async_mark_done()`. Keys and defaults live in `const.py`. Don't duplicate them.
- **Keep strings complete in all languages.** User-facing text goes in every language file that covers it:
  - integration UI (forms, entities, actions, errors): `translations/*.json`
  - card: `frontend/src/strings.ts`
  - notifications: `MESSAGES` in `notifications.py`
  - the Interval sensor's state: `INTERVAL_TEXTS` in `sensor.py`
- **Match the surrounding code.** Python is linted with every ruff rule (`.ruff.toml`). Use HA helpers (`dt_util`, `cv`, selectors) rather than hand-rolled ones, and never block the event loop.
- **Don't break other installs.** Never rename entity IDs, service fields or stored keys without a migration.

## Release

1. Bump `VERSION` in `const.py`.
2. Rebuild `frontend/dist` if the card changed, open a PR and merge it once CI is green.
3. Create a GitHub release with tag `vX.Y.Z` on `main`. `release.yml` runs the tests and the frontend build again, then checks that the tag matches `VERSION`. It patches the manifest version and attaches `home_maintenance.zip`, which HACS installs.

If the release workflow fails, the release has no zip and HACS can't install it. Delete the release, fix the problem, then create the release again.

The zip is flat: `./* translations/* frontend/dist/*`. A new subfolder that must ship has to be added to `release.yml`.

## Pitfalls

These have all bitten before:

- **Browser cache.** The card's URL carries `?v=VERSION`, otherwise browsers keep the old JS after an update. That's one reason to bump `VERSION` on every release.
- **Scoped element registry.** HA's frontend swaps in a scoped custom-element registry at startup and forgets anything defined before. That's why the card waits for `home-assistant` to be defined before it defines itself. Guard every `customElements.define` with `customElements.get`, since the scripts can load twice.
- **HA frontend internals change.** 1.x had a custom sidebar panel built on internal `ha-*` elements, and HA frontend updates broke it twice. That's why tasks now use HA's own forms. Keep the card on documented card APIs (`hass`, `setConfig`, `hass-action`, `ha-form` in the editor).
- **probatio, not voluptuous.** Since 2026.9, Home Assistant validates with `probatio`. Import `probatio as vol`. HA's helpers, such as `add_suggested_values_to_schema`, only recognise probatio markers.
- **Form sections are required keys.** The frontend always sends a section's dict. Tests that submit a task form must include them (`runtime`, `notifications`).
- **Deprecated registry lookups.** `device_registry.async_get_device` is deprecated. Use `async_get_device_by_identifier(identifier, entry_id)`.
- **Dates and DST.** `next_due` keeps the UTC offset of `last_performed`. In the browser, build dates from the `YYYY-MM-DD` part; don't convert to local time, which shifts the day across DST changes.
- **Config entry version.** 1.x entries stored the version as the string `"1.1.0"`, which HA can't compare with an integer. `async_setup` turns it into `1` before migration runs. The config flow is now at version 2, so tests use `MockConfigEntry(version=2)`.
- **Time-dependent tests.** The test time zone is US/Pacific. Freeze the clock (`freezer`) when a test depends on the time of day.
- **Service targets.** `reset_last_performed` takes `entity_id` as a list (`cv.entity_ids`) because dashboard actions send a target.
- **`_attr_*` class attributes become properties.** HA's entity metaclass turns `_attr_translation_key` and friends into properties on the class, so `SomeEntity._attr_translation_key` returns a property object. Read such values from an instance, or keep them in a plain class attribute (`TaskSensor.key`).
- **Translated units are English only.** Home Assistant reads `entity.sensor.<key>.unit_of_measurement` from the English translations whatever the language. That's why the Interval sensor's state is text ("3 mois") from `INTERVAL_TEXTS`, rather than a number with a translated unit.
- **Float noise.** `100 * (1 - 70 / 100)` is `30.000000000000004`, which isn't `<= 30`. `RuntimeTracker.remaining()` rounds to 6 decimals before thresholds see it, and displayed values go through `round_up()` in `runtime.py` rather than a bare `math.ceil`.
- **Delayed saves postpone.** `Store.async_delay_save()` moves a pending write to the latest requested time, so calling it on every tick never writes. The tracker only asks for a save on changes and every 10 minutes.

## Working on the maintainer's Home Assistant

- Integration updates go through HACS. Restart HA after an update, then hard-refresh the browser.
- Ask before changing their dashboards, automations or options. Never edit `.storage` files directly.
- Commit with the GitHub noreply identity configured for this repo, never a personal email.
