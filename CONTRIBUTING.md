# Contributing to Neony

> [贡献指南 (中文)](CONTRIBUTING.zh.md)

Thank you for considering a contribution. Neony is a pre-beta project —
feedback, bug reports and pull requests are all welcome. This document
explains the project's conventions and how to contribute effectively.

---

## Project conventions

These are the ground rules. Contributions that break them will likely be
sent back for revision.

### 1. Pure Python API

Users never touch HTML, JavaScript or CSS strings. Everything — layouts,
styles, events, window control — is exposed as Python objects. Do not
expose raw JS/HTML mechanisms in the public API; internals (like
`data-window-action` or browser-side plumbing) stay internal.

### 2. State is managed internally

Components own their state. Programmatic changes update the DOM but
never fire callbacks; user-driven events carry `source == "user"`.
Follow the existing `Component` pattern: encapsulate a `DOMElement` tree
(composition, not inheritance), build it in `__init__` as `self._root`,
bind events with `_bind()`, sync state in `_on_event()`.

Exceptions and follow-on conventions:

- **Lifecycle pseudo-events are the one exception** — `open`/`close`
  style pseudo-events (`_dispatch_pseudo`) fire on programmatic writes
  by design (see `Dialog.open`).
- **`_bound_events` must equal the event set the component actually
  dispatches internally** — declaring a type it never dispatches makes
  the user's `on_*` callbacks dead.
- **Raw handlers that bypass `_bind` must set `event.source = "user"`
  manually** (or route through `_bind` so the base tags it).
- **Scroll-bearing / self-bounding components must be mounted in a
  definite-height flex parent.** Self-bounding containers use
  `flex-grow + flex-basis:0 + min-height:0`; scroll elements also need
  an explicit height basis (`height:100%` on the cross axis). Mounted
  in an auto-height parent, scrolling breaks and the component pushes
  the page open. Implement new components this way and state the
  mounting contract in the docstring.

### 3. Theming through tokens

Components reference theme colours via `Color(var="--color-*")` so a
theme switch only replaces the `:root` variable block — no DOM diff.
Never hard-code colours that should follow the theme.

### 4. Bilingual documentation

Documentation is split by language — English as the primary language,
Chinese as a separate file:

- `readme.md` (EN) / `readme.zh.md` (中文)
- `docs/api/*.en.md` / `docs/api/*.zh.md`
- `CONTRIBUTING.md` / `CONTRIBUTING.zh.md`

New features must update both language versions.

### 5. Demos live at the repository root

Working demos are `demo_*.py` files at the root (e.g. `demo_custom_window.py`).
The component gallery is the exception — it lives in the `neony.gallery`
package (`uv run gallery`).  New components should ship with a demo, and the
demo should be added to `.zed/tasks.json`.

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
uv run gallery                      # component gallery demo
uv run demo_custom_window.py        # frameless window demo
uv run demo_multi_window.py         # multi-window demo
uv run python scripts/check_all.py  # full check suite — ruff / pyrefly / pytest / vitest
```

The browser-side runtime (event delegation, click-away handling) has its
own JS test suite under `tests/js/`, run by `scripts/check_all.py`
(vitest in jsdom). A clean checkout has no tracked `node_modules/`; the
check script runs `npm ci` automatically when the directory is absent.
New **Python** components usually don't need JS tests — reach for them
only when you change `src/neony/javascript/*`.

---

## Before submitting

1. **Run the checks** — one command runs the whole suite:
   `uv run python scripts/check_all.py` (ruff check + format, pyrefly,
   pytest, and the JS vitest suite). It exits non-zero if anything fails,
   which is exactly what CI's `test` job runs — so a green local run means
   a green CI. `--fix` applies ruff's auto-fixes first; `--smoke` also
   runs the display-requiring demo smoke tests (needs `xvfb-run` on Linux).
2. **Add tests** — bug fixes need a regression test; new components need
   coverage of build/state/events (see `tests/test_components.py` for
   the patterns).
3. **Update docs** — README (both languages) when behaviour changes
   visibly; the paired `docs/api/*.en.md` / `docs/api/*.zh.md` chapters
   for API changes; `docs/api/README.*` when the chapter list changes;
   and new demos also go into the root README demos table.
4. **Follow Conventional Commits** — prefix commits with a type and
   optional scope: `feat(scope):`, `fix(scope):`, `perf(scope):`,
   `refactor(scope):`, `docs:`, `chore:`, ... The changelog
   (`CHANGELOG.md`) is maintained manually; the GitHub release
   description is generated by GitHub from the commit list.

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
changes (window bridge, renderer internals, theming), license changes,
new runtime dependencies.

**Note on platforms:** the roadmap currently marks Windows/WebView2 and Linux
Wayland as verified targets. macOS/WKWebView and HiDPI/mixed-DPI behavior still
need dedicated verification. X11 is used by CI's headless Xvfb startup checks,
but is not a complete desktop support commitment. When submitting a
platform-specific change, state exactly what you verified.

---

## License

By contributing you agree that your work is licensed under the project's
[Apache-2.0](LICENSE).
