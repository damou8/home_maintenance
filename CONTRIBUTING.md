# Contribution guidelines

Contributions are welcome, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## GitHub is used for everything

Issues track bugs and feature requests, and changes come in as pull requests:

1. Fork the repo and create your branch from `main`.
2. Make your change, with a test when it changes behaviour.
3. Update the documentation (`README.md`) if users will notice the change.
4. Check that lint, tests and the frontend build pass (see below).
5. Open the pull request.

[`CLAUDE.md`](CLAUDE.md) describes the code layout, the conventions and the pitfalls to know about. It's worth a read before a first change.

## Development setup

The repo includes a [dev container](.devcontainer.json) for VS Code with Python, Node and a Home Assistant instance ready to run. Without it:

```bash
scripts/setup        # .venv with Home Assistant (minimum supported version) and ruff
scripts/develop      # HA on http://localhost:8123 with this integration linked in, config in ./config
```

### Python

```bash
scripts/lint                                 # ruff format + ruff check --fix

# In a separate venv: the tests pin their own Home Assistant version
python -m pip install -r requirements_test.txt
python -m pytest -q
```

### Panel and dashboard card

The sources are TypeScript in `custom_components/home_maintenance/panel/src`. The built bundles in `panel/dist` are committed because they ship in the release, so rebuild them with every source change:

```bash
cd custom_components/home_maintenance/panel
npm ci
npm run typecheck
npm run build
```

CI fails if `dist` doesn't match the sources.

## Report bugs using GitHub's [issues](../../issues)

Report a bug by [opening a new issue](../../issues/new/choose). Good bug reports have:

- A quick summary and/or background
- Steps to reproduce, as specific as possible
- What you expected would happen
- What actually happens
- Debug logs, and notes on what you think is happening or what you tried

## License

By contributing, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
