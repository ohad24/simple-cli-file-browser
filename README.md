# CLI File Browser

A simple full-screen terminal file browser for the Linux CLI, built with the
[Textual](https://github.com/textualize/textual) framework. Navigate your
filesystem with the keyboard using Textual's `DirectoryTree` widget.

This version supports directory navigation and a toggleable text-preview side
panel. File operations are planned (see [Roadmap](#roadmap)).

## Install

Install the `fbrowse` CLI from [PyPI](https://pypi.org/project/file-browser/):

```bash
uv tool install file-browser
```

Alternatives:

```bash
pipx install file-browser
pip install file-browser
```

Or install the wheel from [GitHub Releases](https://github.com/ohad24/simple-cli-file-browser/releases):

```bash
# newest release (requires the GitHub CLI)
gh release download --repo ohad24/simple-cli-file-browser \
  --pattern '*.whl' --dir /tmp/fbrowse
uv tool install /tmp/fbrowse/*.whl
```

(`pipx install /tmp/fbrowse/*.whl` works too if you don't use uv.)

After install, run `fbrowse` or `fbrowse /path/to/dir` — no `uv run` needed.
If the command isn't found, run `uv tool update-shell` (or `pipx ensurepath`) and restart
your shell.

## Prerequisites

For development from source:

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** for dependency management

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

## Setup

Clone the repo, then install the dependencies into a local virtual environment
(`.venv`) from the lockfile:

```bash
uv sync
```

That's it. `uv sync` reads `pyproject.toml` / `uv.lock` and installs everything
(including this package) into `.venv`.

<details>
<summary>How the project was created from scratch (for reference)</summary>

```bash
uv init --name file-browser   # create pyproject.toml
uv add textual                # runtime dependency
uv add --dev textual-dev      # dev console / tooling
```

</details>

## Running

Start in the current directory:

```bash
uv run fbrowse
```

Equivalent module form:

```bash
uv run python -m file_browser
```

Start in a specific directory:

```bash
uv run fbrowse /path/to/dir
```

## Key bindings

| Key             | Action                                   |
| --------------- | ---------------------------------------- |
| `Up` / `Down`   | Move the selection                       |
| `Right` / `Enter` | Expand the highlighted folder          |
| `Left`          | Collapse the current folder              |
| `Backspace`     | Reroot the tree at the parent directory  |
| `r`             | Refresh / reload the tree                |
| `p`             | Toggle the text-preview side panel       |
| `c`             | Open Claude Code in the highlighted directory |
| `q`             | Quit                                     |

The current root directory is shown in the header subtitle.

## Claude Code integration

Press `c` to launch the [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
CLI in the highlighted directory (or the parent directory of the highlighted
file). The browser is suspended while `claude` runs and resumes when you exit
Claude, reloading the tree to pick up any changes.

This requires the `claude` CLI to be installed and available on your `PATH`. If
it isn't found, the browser shows an error notification and stays open.

## Debugging (dev console)

Textual provides a dev console that streams logs and events from the app. Run
each command in its own terminal:

```bash
# Terminal 1: the console (listens for the app)
uv run textual console

# Terminal 2: run the app in dev mode (connects to the console)
uv run textual run --dev file_browser/browser.py
```

## Testing

Test dependencies (`pytest`, `pytest-asyncio`) are installed automatically by
`uv sync`. Run the suite with:

```bash
uv run pytest        # or: uv run pytest -v
```

The suite covers the `_resolve_start_path` helper (unit tests) and the
`FileBrowserApp` behavior - mounting, parent navigation, refresh, and quit -
via Textual's async `app.run_test()` pilot.

## Releasing

Releases are built and published automatically by GitHub Actions
([`.github/workflows/release.yml`](.github/workflows/release.yml)) whenever a
version tag is pushed. To cut a release:

1. Bump `version` in [`pyproject.toml`](pyproject.toml) and `__version__` in
   [`file_browser/__init__.py`](file_browser/__init__.py) to the new version
   (these must match the tag).
2. Commit the bump.
3. Tag and push:

   ```bash
   git tag v0.1.0
   git push --tags
   ```

The workflow verifies the tag matches the `pyproject.toml` version, runs the
test suite, builds the wheel and sdist with `uv build`, publishes to
[PyPI](https://pypi.org/project/file-browser/) via trusted publishing, and
creates a GitHub Release with those artifacts attached and auto-generated
release notes.

## Roadmap

- [x] **(b) Text preview** - show the contents of the selected file in a
  toggleable side panel (`p`), with syntax highlighting (hook:
  `on_directory_tree_file_selected` in
  [`file_browser/browser.py`](file_browser/browser.py)).
- [ ] **(c) File operations** - copy, move, delete, and rename, bound to keys
  that act on the highlighted node and reload the tree.

## Project layout

```
file_browser/
  __init__.py     # package metadata
  __main__.py     # `python -m file_browser` entry point
  browser.py      # the Textual app (FileBrowserApp + main())
tests/            # pytest suite (helper unit tests + async app tests)
pyproject.toml    # project metadata, deps, and the `fbrowse` script
```
