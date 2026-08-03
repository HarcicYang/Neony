# Contributing to Neony

> [贡献指南 (中文)](CONTRIBUTING.zh.md)

Thank you for considering a contribution. Neony is an alpha project —
feedback, bug reports and pull requests are all welcome. This document
explains the project's conventions and how to contribute effectively.

---

## Project conventions

These are the ground rules. Contributions that break them will likely be
sent back for revision.

### 1. Pure Python API

Users never touch HTML, JavaScript or CSS strings. Everything — layouts,
styles, events, window control — is exposed as Python objects. Do not
expose raw JS/HTML mechanisms in the public API; internals (like the
`data-window-action` attribute or the JS engine) stay internal.

### 2. State is managed internally

Components own their state. Programmatic changes update the DOM but
never fire callbacks; user-driven events carry `source == "user"`.
Follow the existing `Component` pattern: encapsulate a `DOMElement` tree
(composition, not inheritance), build it in `__init__` as `self._root`,
bind events with `_bind()`, sync state in `_on_event()`.

### 3. Theming through tokens

Components reference theme colours via `Color(var="--color-*")` so a
theme switch redraws everything with zero DOM diff. Never hard-code
colours that should follow the theme.

### 4. Bilingual documentation

Documentation is split by language — English as the primary language,
Chinese as a separate file:

- `readme.md` (EN) / `readme.zh.md` (中文)
- `docs/api.en.md` / `docs/api.zh.md`
- `CONTRIBUTING.md` / `CONTRIBUTING.zh.md`

New features must update both language versions.

### 5. Demos live at the repository root

Working demos are `test_*.py` files at the root (e.g. `test_gallery.py`).
New components should ship with a demo, and the demo should be added to
`.zed/tasks.json`.

---

## Development setup

The project uses [uv](https://docs.astral.sh/uv/) for environments and
commands.

```bash
uv sync --group dev     # install dependencies (incl. dev tools)
```

### System dependencies

On Linux you need the WebKitGTK stack:

```bash
sudo apt-get install libwebkit2gtk-4.1-dev libgtk-3-dev libxdo-dev
```

---

## Running the project

```bash
uv run test_gallery.py              # component gallery demo
uv run test_custom_window.py        # frameless window demo
uv run test_multi_window.py         # multi-window demo
uv run pytest -q                    # test suite
uv run ruff check .                 # lint
uv run ruff format .                # format
uv run pyrefly check                # type check
```

---

## Before submitting

1. **Run the checks** — `ruff check`, `ruff format --check`, `pyrefly
   check` and `pytest` must all pass. CI runs the same commands.
2. **Add tests** — bug fixes need a regression test; new components need
   coverage of build/state/events (see `tests/test_components.py` for
   the patterns).
3. **Update docs** — README (both languages) when behaviour changes
   visibly; `docs/api.en.md` / `docs/api.zh.md` for API changes.
4. **Update the changelog** — add an entry under the unreleased section
   in `CHANGELOG.md`.

## Pull request workflow

1. Fork the repository and create a branch (`fix/...`, `feat/...`).
2. Make your change with tests and docs as above.
3. Open a PR against `master`. Describe what changed and why, and note
   anything platform-specific you verified (e.g. "tested on Linux/hyprland").
4. CI must pass before merge.

## Scope of contributions

**Welcome:** bug fixes, new components that follow the existing patterns,
documentation improvements, test coverage, UX polish.

**Discuss first (open an issue):** large API changes, architecture
changes (bridge, diff engine, theming), license changes, new runtime
dependencies.

**Note on platforms:** the project is currently developed and verified
on Linux. Windows/macOS support is untested — platform-specific fixes are
welcome, but be explicit about what you verified.

---

## License

By contributing you agree that your work is licensed under the project's
[LGPL-3.0-or-later](LICENSE).
