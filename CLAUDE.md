# Home Maintenance

Home Assistant custom integration (domain `home_maintenance`), installed through HACS. It tracks recurring tasks. Each task is a `binary_sensor` that turns `on` when the task is due. The integration also has a sidebar panel to manage tasks, a dashboard card and daily notifications for due tasks.

Fork of TJPoorman/home_maintenance, maintained at github.com/damou8/home_maintenance. Minimum Home Assistant version: 2026.3 (`hacs.json`).

## Layout

```
custom_components/home_maintenance/
  __init__.py        setup/unload, services, NFC tag listener
  binary_sensor.py   task entities; compute_next_due() is the only due-date calculation
  store.py           TaskStore: tasks in .storage/home_maintenance.storage (attrs classes)
  websocket.py       home_maintenance/* commands used by the panel
  notifications.py   TaskNotifier: daily notify.send_message; messages in en/fr/de
  config_flow.py     setup + options (sidebar, notification defaults); schemas in const.py
  panel.py           registers the panel and the card's JS (frontend.add_extra_js_url)
  translations/      config/options strings (en, de, fr)
  panel/             TypeScript sources (Lit + esbuild)
    src/main.ts      sidebar panel
    src/card/        dashboard card, its editor and its own strings (en/fr/de)
    localize/        panel strings (en, de); missing keys fall back to English
    dist/            built bundles, committed: they ship in the release zip
tests/               pytest with pytest-homeassistant-custom-component
```

## Commands

```bash
# Python tests (CI: Tests). Use their own venv: they pin a newer HA than requirements.txt
python -m pip install -r requirements_test.txt
python -m pytest -q

# Python lint (CI: Lint). ruff comes from requirements.txt (scripts/setup)
ruff check . && ruff format --check .     # scripts/lint fixes instead of checking

# Panel and card (CI: Frontend)
cd custom_components/home_maintenance/panel
npm ci
npm run typecheck
npm run build                             # then commit dist/ with the sources

# A throwaway HA on port 8123 with this integration linked in
scripts/setup && scripts/develop
```

## Good practices

- **Keep CI green.** The Lint, Tests, Frontend and Validate (hassfest and HACS) workflows run on every PR. Frontend fails when `dist/` doesn't match the sources.
- **Test behaviour changes.** Add a pytest for each bug fix and new feature, and drive the integration the way users do: websocket commands, services, the options flow. The fixtures are in `tests/conftest.py`.
- **Stay backward compatible with stored tasks.** A new task field needs an `attr.ib` default in `store.py` so older storage files still load. It also has to be added in `websocket.py` (the `add_task` schema and `TASK_UPDATES_SCHEMA`), in `panel/src/types.ts`, and in a test that loads old storage.
- **Keep one source of truth.** Due dates come from `compute_next_due()`. Option keys and defaults live in `const.py`. Don't duplicate either.
- **Keep strings complete in all languages.** User-facing text goes in every language file that covers it:
  - integration UI: `translations/*.json`
  - panel: `panel/localize/languages/*.json`
  - card: `panel/src/card/strings.ts`
  - notifications: `MESSAGES` in `notifications.py`
- **Match the surrounding code.** Python is linted with every ruff rule (`.ruff.toml`). Use HA helpers (`dt_util`, `cv`, selectors) rather than hand-rolled ones, and never block the event loop.
- **Don't break other installs.** Never rename entity IDs, service fields or stored keys without a migration.

## Release

1. Bump the version in **both** `const.py` (`VERSION`) and `panel/src/const.ts`. A test checks they match.
2. Rebuild `panel/dist`, then commit and push to `main`.
3. Create a GitHub release with tag `vX.Y.Z`. `release.yml` patches the manifest version and attaches `home_maintenance.zip`, which HACS installs.

The zip is flat: `./* translations/* panel/dist/*`. A new subfolder that must ship has to be added to `release.yml`.

## Pitfalls

These have all bitten before:

- **Browser cache.** The panel and card URLs carry `?v=VERSION`, otherwise browsers keep the old JS after an update. That's one reason to bump `VERSION` on every release.
- **Scoped element registry.** HA's frontend swaps in a scoped custom-element registry at startup and forgets anything defined before. That's why the card waits for `home-assistant` to be defined before it defines itself. Guard every `customElements.define` with `customElements.get`, since the scripts can load twice.
- **Table cell styles.** `ha-data-table` cells render inside the table's shadow DOM, so panel CSS doesn't reach them. Style cell templates inline.
- **HA frontend components change.** Since 2026, `ha-dialog` is WebAwesome-based (`header-title`, `ha-dialog-footer`, `data-dialog="close"`), menus are `ha-dropdown` with `@wa-select`, and `mwc-button` and `ha-md-menu` are gone. Check the frontend source for the HA version you target before using an `ha-*` element.
- **Dates and DST.** `next_due` keeps the UTC offset of `last_performed`. In the browser, build dates from the `YYYY-MM-DD` part; don't convert to local time, which shifts the day across DST changes.
- **Config entry version.** The config flow `VERSION` is the string `"1.1.0"`, and real entries store it. Tests must use `MockConfigEntry(version="1.1.0")`. Changing it triggers `async_migrate_entry`.
- **Service targets.** `reset_last_performed` takes `entity_id` as a list (`cv.entity_ids`) because dashboard actions send a target.

## Working on the maintainer's Home Assistant

- Integration updates go through HACS. Restart HA after an update, then hard-refresh the browser.
- Ask before changing their dashboards, automations or options. Never edit `.storage` files directly.
- Commit with the GitHub noreply identity configured for this repo, never a personal email.
