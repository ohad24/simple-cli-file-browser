"""A simple terminal file browser built with Textual.

Supports directory navigation and a toggleable text-preview side panel. See the
TODO marker below for the remaining deferred feature (file operations).
"""

from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import DirectoryTree, Footer, Header, TextArea

# Read at most this many bytes when previewing a file, to stay responsive on
# large files.
_PREVIEW_BYTE_LIMIT = 256 * 1024

# Map file extensions to TextArea syntax-highlighting languages. Extensions not
# listed here fall back to plain text (no highlighting).
_LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".md": "markdown",
    ".markdown": "markdown",
    ".json": "json",
    ".toml": "toml",
    ".js": "javascript",
    ".mjs": "javascript",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".sh": "bash",
    ".bash": "bash",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".sql": "sql",
    ".xml": "xml",
}


class FileBrowserApp(App):
    """A minimal file browser: navigate the directory tree with the keyboard."""

    TITLE = "CLI File Browser"

    CSS = """
    #tree { width: 1fr; }
    #preview { width: 2fr; display: none; }
    #preview.visible { display: block; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("backspace", "go_to_parent", "Parent dir"),
        Binding("r", "refresh_tree", "Refresh"),
        Binding("p", "toggle_preview", "Preview"),
    ]

    def __init__(self, start_path: Path) -> None:
        super().__init__()
        self._start_path = start_path
        self._selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield DirectoryTree(str(self._start_path), id="tree")
            yield TextArea.code_editor("", read_only=True, id="preview")
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

    def action_toggle_preview(self) -> None:
        """Show or hide the preview panel, loading the selection when shown."""
        preview = self.query_one("#preview", TextArea)
        preview.toggle_class("visible")
        if preview.has_class("visible"):
            self._load_preview(self._selected_path)

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        self._selected_path = Path(event.path)
        preview = self.query_one("#preview", TextArea)
        if preview.has_class("visible"):
            self._load_preview(self._selected_path)

    def _load_preview(self, path: Path | None) -> None:
        """Read ``path`` (subject to a size cap) into the preview TextArea."""
        preview = self.query_one("#preview", TextArea)
        if path is None:
            preview.load_text("")
            preview.language = None
            return

        try:
            data = path.read_bytes()[:_PREVIEW_BYTE_LIMIT]
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            preview.language = None
            preview.load_text("[binary file - no preview]")
            return
        except OSError as error:
            preview.language = None
            preview.load_text(f"[could not read file: {error}]")
            return

        preview.language = _LANGUAGE_BY_SUFFIX.get(path.suffix.lower())
        preview.load_text(text)

    def _update_subtitle(self, path: Path) -> None:
        self.sub_title = str(path)

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
