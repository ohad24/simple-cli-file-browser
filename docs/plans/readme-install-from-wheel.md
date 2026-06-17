# README: Install from the latest wheel

Add a new "Install" section to [README.md](../../README.md) explaining how end users install the `filebrowser` CLI from the wheel attached to GitHub Releases (produced by the release workflow in [.github/workflows/release.yml](../../.github/workflows/release.yml)).

## Placement

Insert the section after "Prerequisites"/before "Setup" (which is dev-oriented), so end users see the install path first. Keep "Setup" as the from-source/dev flow.

## Content

Document two approaches:

### Option A (recommended): `gh` CLI — gets the newest wheel without knowing the version

```bash
gh release download --repo ohad24/simple-cli-file-browser \
  --pattern '*.whl' --dir /tmp/filebrowser
uv tool install /tmp/filebrowser/*.whl
```

Also note the `pipx install /tmp/filebrowser/*.whl` equivalent for users without uv.

### Option B: direct URL (must include the version in the filename)

```bash
uv tool install \
  https://github.com/ohad24/simple-cli-file-browser/releases/latest/download/file_browser-0.1.0-py3-none-any.whl
```

Explain that GitHub's `releases/latest/download/<asset>` requires the exact asset name, which contains the version (e.g. `file_browser-0.1.0-py3-none-any.whl`), so the version must be updated when newer releases are cut. Mention `pip install <url>` as an alternative.

After install, the `filebrowser` command is on PATH (via `uv tool` / `pipx`), runnable as `filebrowser [path]` without `uv run`.

### Usage after install

Once installed, the `filebrowser` command is available directly on your `PATH` (no `uv run` needed — that is only for the from-source/dev flow):

```bash
# Start in the current directory
filebrowser

# Start in a specific directory
filebrowser /path/to/dir
```

This works because [pyproject.toml](../../pyproject.toml) declares the `filebrowser` entry point under `[project.scripts]` (`file_browser.browser:main`).

Tip: if `filebrowser` isn't found after install, the tool bin directory isn't on your `PATH` — run `uv tool update-shell` (or `pipx ensurepath`), then restart your shell. Verify the install with `uv tool list` (or `pipx list`).

## Notes / decisions

- Lead with the `gh` approach because it truly resolves "latest"; the direct URL is a fallback that requires a known version.
- Use `uv tool install` as the primary command since the project already standardizes on uv, with `pipx`/`pip` noted as alternatives.
- No code/workflow changes — documentation only.
