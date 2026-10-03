"""Async tests for FileBrowserApp driven via Textual's run_test() pilot."""

import contextlib
from collections import namedtuple
from pathlib import Path

from textual.widgets import DirectoryTree, Footer, Header, TextArea

from file_browser import browser as browser_module
from file_browser.browser import (
    _DEFAULT_FILE_ICON,
    _ICON_BY_SUFFIX,
    FileBrowserApp,
    FileIconDirectoryTree,
    _claude_target_dir,
    _file_icon,
    _get_git_info,
)

# Lightweight stand-in for subprocess.CompletedProcess used in git tests.
_FakeResult = namedtuple("_FakeResult", ["returncode", "stdout"])


def test_file_icon_known_extension():
    assert _file_icon(Path("main.py")) == _ICON_BY_SUFFIX[".py"]


def test_file_icon_is_case_insensitive():
    assert _file_icon(Path("README.MD")) == _ICON_BY_SUFFIX[".md"]


def test_file_icon_unknown_extension_falls_back():
    assert _file_icon(Path("data.unknownext")) == _DEFAULT_FILE_ICON


def test_file_icon_no_extension_falls_back():
    assert _file_icon(Path("Makefile")) == _DEFAULT_FILE_ICON


async def test_tree_uses_icon_subclass(tmp_path):
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one(DirectoryTree)
        assert isinstance(tree, FileIconDirectoryTree)


async def test_tree_renders_file_type_icon(tmp_path):
    (tmp_path / "hello.py").write_text("print('hi')\n")
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one(FileIconDirectoryTree)
        await tree.reload()
        await pilot.pause()
        py_node = next(
            child
            for child in tree.root.children
            if child.data is not None and child.data.path.name == "hello.py"
        )
        label = tree.render_label(py_node, tree.rich_style, tree.rich_style)
        assert label.plain.startswith(_ICON_BY_SUFFIX[".py"])


def test_claude_target_dir_for_directory(tmp_path):
    assert _claude_target_dir(tmp_path) == tmp_path


def test_claude_target_dir_for_file(tmp_path):
    target = tmp_path / "hello.py"
    target.write_text("print('hello')\n")
    assert _claude_target_dir(target) == tmp_path


async def test_open_claude_runs_with_highlighted_cwd(tmp_path, monkeypatch):
    recorded = {}

    def fake_run(args, **kwargs):
        # git calls from _get_git_info: simulate "not a repo" cleanly.
        if args and args[0] == "git":
            return _FakeResult(1, "")
        recorded["args"] = args
        recorded["cwd"] = kwargs.get("cwd")

    monkeypatch.setattr(browser_module.shutil, "which", lambda _: "/usr/bin/claude")
    monkeypatch.setattr(browser_module.subprocess, "run", fake_run)

    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        monkeypatch.setattr(app, "suspend", contextlib.nullcontext)
        await pilot.press("c")
        await pilot.pause()

    assert recorded["args"] == ["/usr/bin/claude"]
    assert recorded["cwd"] == str(tmp_path)


async def test_mounts_with_widgets_and_subtitle(tmp_path):
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one(DirectoryTree) is not None
        assert app.query_one(Header) is not None
        assert app.query_one(Footer) is not None
        preview = app.query_one("#preview", TextArea)
        assert not preview.has_class("visible")
        assert app.sub_title == str(tmp_path)


async def test_toggle_preview_shows_panel(tmp_path):
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        preview = app.query_one("#preview", TextArea)
        await pilot.press("p")
        await pilot.pause()
        assert preview.has_class("visible")
        await pilot.press("p")
        await pilot.pause()
        assert not preview.has_class("visible")


async def test_preview_loads_file_contents(tmp_path):
    target = tmp_path / "hello.py"
    target.write_text("print('hello')\n")
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._selected_path = target
        await pilot.press("p")
        await pilot.pause()
        preview = app.query_one("#preview", TextArea)
        assert preview.text == "print('hello')\n"
        assert preview.language == "python"


async def test_preview_binary_file(tmp_path):
    target = tmp_path / "blob.bin"
    target.write_bytes(b"\xff\xfe\x00\x01binary")
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._selected_path = target
        await pilot.press("p")
        await pilot.pause()
        preview = app.query_one("#preview", TextArea)
        assert preview.text == "[binary file - no preview]"
        assert preview.language is None


async def test_backspace_navigates_to_parent(tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    app = FileBrowserApp(child)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("backspace")
        await pilot.pause()
        tree = app.query_one(DirectoryTree)
        assert Path(tree.path) == tmp_path
        assert app.sub_title == str(tmp_path)


async def test_backspace_at_root_is_noop(tmp_path):
    root = Path(tmp_path.anchor)
    app = FileBrowserApp(root)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("backspace")
        await pilot.pause()
        tree = app.query_one(DirectoryTree)
        assert Path(tree.path) == root


async def test_descend_navigates_into_highlighted_dir(tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one(DirectoryTree)
        node = next(
            c
            for c in tree.root.children
            if c.data is not None and c.data.path.name == "child"
        )
        tree.cursor_line = node.line
        await pilot.pause()
        await pilot.press("l")
        await pilot.pause()
        assert Path(tree.path) == child
        assert app.sub_title == str(child)


async def test_descend_on_file_is_noop(tmp_path):
    (tmp_path / "hello.py").write_text("print('hi')\n")
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one(DirectoryTree)
        node = next(
            c
            for c in tree.root.children
            if c.data is not None and c.data.path.name == "hello.py"
        )
        tree.cursor_line = node.line
        await pilot.pause()
        await pilot.press("l")
        await pilot.pause()
        assert Path(tree.path) == tmp_path


async def test_refresh_keeps_tree(tmp_path):
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
        assert app.query_one(DirectoryTree) is not None


async def test_quit_exits_app(tmp_path):
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()
    assert app._return_value is None
    assert not app.is_running


async def test_goto_dir_exits_with_highlighted_dir(tmp_path):
    child = tmp_path / "subdir"
    child.mkdir()
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one(DirectoryTree)
        node = next(
            c
            for c in tree.root.children
            if c.data is not None and c.data.path.name == "subdir"
        )
        tree.cursor_line = node.line
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()
    assert app._return_value == child


async def test_goto_dir_on_file_uses_parent(tmp_path):
    (tmp_path / "hello.py").write_text("print('hi')\n")
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one(DirectoryTree)
        node = next(
            c
            for c in tree.root.children
            if c.data is not None and c.data.path.name == "hello.py"
        )
        tree.cursor_line = node.line
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()
    assert app._return_value == tmp_path


# ---------------------------------------------------------------------------
# _get_git_info unit tests
# ---------------------------------------------------------------------------


def test_get_git_info_not_in_repo(tmp_path, monkeypatch):
    # Simulate git returning a non-zero exit code (not a repo) without
    # hitting the real git binary so the test is environment-independent.
    monkeypatch.setattr(
        browser_module.subprocess,
        "run",
        lambda *a, **k: _FakeResult(128, "fatal: not a git repository\n"),
    )
    assert _get_git_info(tmp_path) is None


def test_get_git_info_returns_branch(tmp_path, monkeypatch):
    monkeypatch.setattr(
        browser_module.subprocess,
        "run",
        lambda *a, **k: _FakeResult(0, "## main...origin/main\n"),
    )
    assert _get_git_info(tmp_path) == "⎇ main"


def test_get_git_info_dirty_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(
        browser_module.subprocess,
        "run",
        lambda *a, **k: _FakeResult(0, "## main...origin/main\n M file.py\n"),
    )
    assert _get_git_info(tmp_path) == "⎇ main *"


def test_get_git_info_git_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(
        browser_module.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()),
    )
    assert _get_git_info(tmp_path) is None


def test_get_git_info_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr(
        browser_module.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(
            browser_module.subprocess.TimeoutExpired("git", 2)
        ),
    )
    assert _get_git_info(tmp_path) is None


async def test_subtitle_includes_git_branch(tmp_path, monkeypatch):
    monkeypatch.setattr(
        browser_module.subprocess,
        "run",
        lambda *a, **k: _FakeResult(0, "## feat/my-branch...origin/feat/my-branch\n"),
    )
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
    assert "⎇ feat/my-branch" in app.sub_title
