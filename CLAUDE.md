# Home Maintenance

Home Assistant custom integration (domain `home_maintenance`), installed through HACS. It tracks recurring tasks. Each task is a config subentry, managed from the integration's page with HA's own forms. A task is due after a calendar interval, a runtime limit (hours while an entity is on), or whichever comes first. It's shown as a device with a `binary_sensor` that turns `on` when the task is due, date `sensor`s (last done, next due), an Interval `sensor` for a calendar interval, Remaining, Hours left and Lifespan `sensor`s for a runtime limit, and a "Mark done" `button`. The integration also has a dashboard card and sends daily notifications for due tasks.

Fork of TJPoorman/home_maintenance, maintained at github.com/damou8/home_maintenance. Minimum Home Assistant version: 2026.9 (`hacs.json`), the first release that uses `probatio` instead of `voluptuous`. When raising it to 2026.10 or later, remove the `single_instance_allowed` abort from the translations: Home Assistant translates it itself since 2026.10.

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
docs/                intent and spec of larger features (intent/, specs/)
```

### How a task is stored and updated

- A task is a `ConfigSubentry` of type `task`. Its title is the task title. Its `data` holds the interval (`interval_value` is `None` for a task with only a runtime limit), the runtime limit (`runtime_entity`, `runtime_hours`), `last_performed` (local midnight, ISO), icon, tag, `enabled` and the notification override. Its `unique_id` is the task ID used in the entities' unique IDs.
- The hours used aren't in the subentry: they change every minute, and saving a subentry writes the config entries file and fires the update listener. `RuntimeTracker` keeps them in its own `Store`, saved on every on/off change, every 10 minutes while counting, when HA stops and when the entry unloads. `async_mark_done()` resets them, and the task forms can correct them. `docs/specs/runtime-tasks.md` has the full design.
- Every change to a subentry or to the options fires the entry's update listener (`_async_entry_updated`). It compares a signature of the options and tasks, leaving out `last_performed`:
  - Anything else changed (task added, changed or deleted, options saved): the entry reloads.
  - Only `last_performed` changed (a task was marked done): the entities in `runtime_data.entities` update in place (`async_task_updated`), without a reload.
- Because the listener does the reloading, flows end with `async_update_and_abort()`, never `async_update_reload_and_abort()`. That would reload the entry twice, and Home Assistant raises an error for it from 2026.12.

## Commands

```bash
# Python tests (CI: Tests). Use their own venv: they pin a newer HA than requirements.txt
python -m pip install -r requirements_test.txt
python -m pytest -q

# Python lint (CI: Lint), with every ruff rule (.ruff.toml). ruff comes from requirements.txt (scripts/setup)
ruff check . && ruff format --check .     # scripts/lint fixes instead of checking

# Dashboard card (CI: Frontend)
cd custom_components/home_maintenance/frontend
npm ci
npm run typecheck
npm run build                             # then commit dist/ with the sources

# A throwaway HA on port 8123 with this integration linked in
scripts/setup && scripts/develop
```

Tests drive the integration through its real forms: `add_task()` in `tests/conftest.py` goes through the task flow. A test that submits a task form must include the `runtime` and `notifications` section dicts. The config flow is at version 2, so tests use `MockConfigEntry(version=2)`.

## Conventions

- **CI and `main`.** Lint, Tests, Frontend and Validate (hassfest and HACS) run on every PR. Frontend fails when `dist/` doesn't match the sources. The "Protect main" ruleset makes changes go through a PR that merges only when these checks pass.
- **Workflow actions are updated by hand.** `.github/dependabot.yml` comes from upstream, but Dependabot doesn't run on this fork. Actions use floating major tags (`actions/checkout@v7`), and the hassfest and HACS validators follow `master`/`main`, as their docs recommend. Move to a new major version when GitHub warns about a deprecated runtime.
- **Adding a task field.** Read it with `.get()` and a default, since existing subentries don't have it. Add it to the task form in `config_flow.py` (`_task_schema`, `_form_values`, `_parse_task_input`) and to the translations. A change in the stored format needs a new config entry version and a step in `async_migrate_entry`.
- **One source of truth.**
  - Due dates come from `compute_next_due()`.
  - Runtime comes from `RuntimeTracker` (`remaining()`, `hours_left()`). Displayed runtime values go through `round_up()` in `runtime.py`, which removes float noise before rounding up.
  - Marking done goes through `async_mark_done()`.
  - Keys and defaults live in `const.py`.
- **Strings in en, fr and de.** User-facing text goes in every language file that covers it:
  - integration UI (forms, entities, actions, errors, repair issues): `translations/*.json`
  - card: `frontend/src/strings.ts`
  - notifications: `MESSAGES` in `notifications.py`
  - the Interval sensor's state: `INTERVAL_TEXTS` in `sensor.py`. It's text ("3 mois") because Home Assistant only reads translated units from English.

## Release

1. Bump `VERSION` in `const.py`. It is also the card's cache-busting query (`?v=VERSION`), so browsers only load a new card after a version bump.
2. Rebuild `frontend/dist` if the card changed, open a PR and merge it once CI is green.
3. Create a GitHub release with tag `vX.Y.Z` on `main`. `release.yml` runs the tests and the frontend build again, then checks that the tag matches `VERSION`. It patches the manifest version and attaches `home_maintenance.zip`, which HACS installs.

If the release workflow fails, the release has no zip and HACS can't install it. Delete the release, fix the problem, then create the release again.

The zip is flat: `./* translations/* frontend/dist/*`. A new subfolder that must ship has to be added to `release.yml`.

## Pitfalls

These have all bitten before:

- **No custom panel.** 1.x had a sidebar panel built on internal `ha-*` elements, and HA frontend updates broke it twice. That's why tasks use HA's own forms. Keep the card on documented card APIs (`hass`, `setConfig`, `hass-action`, `ha-form` in the editor).
- **Dates and DST.** `next_due` keeps the UTC offset of `last_performed`. The card builds dates from the `YYYY-MM-DD` part.
- **Config entry version.** 1.x entries stored the version as the string `"1.1.0"`, which HA can't compare with an integer. `async_setup` turns it into `1` before migration runs.
- **Daily check in tests.** The notifier runs every day at 09:00 (`DEFAULT_NOTIFY_TIME`) and sends its own messages. Tests that move the clock by hours start at 10:00 (the `morning` fixture in `tests/test_runtime.py`) and keep runtime limits short enough not to reach the next 09:00.

## Working on the maintainer's Home Assistant

- Integration updates go through HACS, never by copying files.
- Ask before changing their dashboards, automations or options.
