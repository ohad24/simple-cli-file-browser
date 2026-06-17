"""Async tests for FileBrowserApp driven via Textual's run_test() pilot."""

from pathlib import Path

from textual.widgets import DirectoryTree, Footer, Header

from file_browser.browser import FileBrowserApp


async def test_mounts_with_widgets_and_subtitle(tmp_path):
    app = FileBrowserApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one(DirectoryTree) is not None
        assert app.query_one(Header) is not None
        assert app.query_one(Footer) is not None
        assert app.sub_title == str(tmp_path)


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
