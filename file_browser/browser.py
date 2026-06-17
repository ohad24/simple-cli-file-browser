"""A simple terminal file browser built with Textual.

v1 supports directory navigation only. See the TODO markers below for the
deferred features (text preview and file operations).
"""

from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DirectoryTree, Footer, Header


class FileBrowserApp(App):
    """A minimal file browser: navigate the directory tree with the keyboard."""

    TITLE = "CLI File Browser"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("backspace", "go_to_parent", "Parent dir"),
        Binding("r", "refresh_tree", "Refresh"),
    ]

    def __init__(self, start_path: Path) -> None:
        super().__init__()
        self._start_path = start_path

    def compose(self) -> ComposeResult:
        yield Header()
        yield DirectoryTree(str(self._start_path), id="tree")
        yield Footer()

    def on_mount(self) -> None:
        self._update_subtitle(self._start_path)

    def action_go_to_parent(self) -> None:
        """Reroot the tree at the parent of the current directory."""
        tree = self.query_one(DirectoryTree)
        current = Path(tree.path)
        parent = current.parent
        if parent != current:
            tree.path = str(parent)
            self._update_subtitle(parent)

    def action_refresh_tree(self) -> None:
        self.query_one(DirectoryTree).reload()

    def _update_subtitle(self, path: Path) -> None:
        self.sub_title = str(path)

    # TODO (b): Preview text file contents.
    # Hook into the selection event to read the chosen file and render it in a
    # side panel (e.g. a Static/TextArea inside a Horizontal layout):
    #
    # def on_directory_tree_file_selected(
    #     self, event: DirectoryTree.FileSelected
    # ) -> None:
    #     ...read event.path and show its contents...

    # TODO (c): File operations (copy, move, delete, rename).
    # Add bindings (e.g. "d" delete, "n" rename) that act on the highlighted
    # node, using shutil/os, then call DirectoryTree.reload() to refresh.


def _resolve_start_path(argv: list[str]) -> Path:
    """Return the directory to start in, from argv[1] or the cwd."""
    if len(argv) > 1:
        candidate = Path(argv[1]).expanduser()
    else:
        candidate = Path.cwd()

    candidate = candidate.resolve()
    if not candidate.exists():
        raise SystemExit(f"Path does not exist: {candidate}")
    if not candidate.is_dir():
        candidate = candidate.parent
    return candidate


def main() -> None:
    start_path = _resolve_start_path(sys.argv)
    FileBrowserApp(start_path).run()


if __name__ == "__main__":
    main()
