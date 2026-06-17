"""A simple terminal file browser built with Textual.

Supports directory navigation and a toggleable text-preview side panel. See the
TODO marker below for the remaining deferred feature (file operations).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from rich.style import Style
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import DirectoryTree, Footer, Header, TextArea
from textual.widgets._tree import TOGGLE_STYLE
from textual.widgets.directory_tree import DirEntry
from textual.widgets.tree import TreeNode

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

# Icons shown to the left of each tree node. Folders use the two icons below;
# files use the per-extension map, falling back to a generic file icon.
_FOLDER_ICON = "📁 "
_FOLDER_OPEN_ICON = "📂 "
_DEFAULT_FILE_ICON = "📄 "

# Map lowercased file extensions to a display icon (with a trailing space).
# Several extensions intentionally share an icon (e.g. all config formats).
_ICON_BY_SUFFIX = {
    # Source / config / docs
    ".py": "🐍 ",
    ".md": "📝 ",
    ".markdown": "📝 ",
    ".rst": "📝 ",
    ".txt": "📄 ",
    ".log": "📜 ",
    ".json": "🔧 ",
    ".toml": "🔧 ",
    ".yaml": "🔧 ",
    ".yml": "🔧 ",
    ".ini": "🔧 ",
    ".cfg": "🔧 ",
    ".conf": "🔧 ",
    ".env": "🔧 ",
    ".js": "📜 ",
    ".mjs": "📜 ",
    ".cjs": "📜 ",
    ".ts": "📜 ",
    ".tsx": "📜 ",
    ".jsx": "📜 ",
    ".html": "🌐 ",
    ".htm": "🌐 ",
    ".css": "🎨 ",
    ".scss": "🎨 ",
    ".sh": "🐚 ",
    ".bash": "🐚 ",
    ".zsh": "🐚 ",
    ".go": "🐹 ",
    ".rs": "🦀 ",
    ".java": "☕ ",
    ".c": "⚙️ ",
    ".h": "⚙️ ",
    ".cpp": "⚙️ ",
    ".hpp": "⚙️ ",
    ".sql": "🗃️ ",
    ".xml": "🗞️ ",
    # Images
    ".png": "🖼️ ",
    ".jpg": "🖼️ ",
    ".jpeg": "🖼️ ",
    ".gif": "🖼️ ",
    ".bmp": "🖼️ ",
    ".svg": "🖼️ ",
    ".webp": "🖼️ ",
    ".ico": "🖼️ ",
    # Audio
    ".mp3": "🎵 ",
    ".wav": "🎵 ",
    ".flac": "🎵 ",
    ".ogg": "🎵 ",
    ".m4a": "🎵 ",
    # Video
    ".mp4": "🎬 ",
    ".mkv": "🎬 ",
    ".mov": "🎬 ",
    ".avi": "🎬 ",
    ".webm": "🎬 ",
    # Documents
    ".pdf": "📕 ",
    # Archives
    ".zip": "📦 ",
    ".tar": "📦 ",
    ".gz": "📦 ",
    ".tgz": "📦 ",
    ".bz2": "📦 ",
    ".xz": "📦 ",
    ".7z": "📦 ",
    ".rar": "📦 ",
    # Binaries / compiled artifacts
    ".exe": "⚙️ ",
    ".bin": "⚙️ ",
    ".so": "⚙️ ",
    ".dll": "⚙️ ",
    ".o": "⚙️ ",
    ".a": "⚙️ ",
}


def _file_icon(path: Path) -> str:
    """Return the display icon (with trailing space) for a file ``path``."""
    return _ICON_BY_SUFFIX.get(path.suffix.lower(), _DEFAULT_FILE_ICON)


class FileIconDirectoryTree(DirectoryTree):
    """A ``DirectoryTree`` that shows per-file-type icons instead of one icon.

    This mirrors Textual's default ``render_label`` styling (folder/file/hidden
    component classes, extension highlighting) but swaps the leading icon based
    on the node's path.
    """

    def render_label(
        self, node: TreeNode[DirEntry], base_style: Style, style: Style
    ) -> Text:
        node_label = node._label.copy()
        node_label.stylize(style)

        # Before mount we can't resolve component styles; defer to the default.
        if not self.is_mounted:
            return node_label

        if node._allow_expand:
            icon = _FOLDER_OPEN_ICON if node.is_expanded else _FOLDER_ICON
            prefix = (icon, base_style + TOGGLE_STYLE)
            node_label.stylize_before(
                self.get_component_rich_style("directory-tree--folder", partial=True)
            )
        else:
            path = node.data.path if node.data is not None else Path(node_label.plain)
            prefix = (_file_icon(path), base_style)
            node_label.stylize_before(
                self.get_component_rich_style("directory-tree--file", partial=True),
            )
            node_label.highlight_regex(
                r"\..+$",
                self.get_component_rich_style(
                    "directory-tree--extension", partial=True
                ),
            )

        if node_label.plain.startswith("."):
            node_label.stylize_before(
                self.get_component_rich_style("directory-tree--hidden", partial=True)
            )

        return Text.assemble(prefix, node_label)


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
        Binding("l", "descend", "Open dir"),
        Binding("r", "refresh_tree", "Refresh"),
        Binding("p", "toggle_preview", "Preview"),
        Binding("c", "open_claude", "Claude Code"),
    ]

    def __init__(self, start_path: Path) -> None:
        super().__init__()
        self._start_path = start_path
        self._selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield FileIconDirectoryTree(str(self._start_path), id="tree")
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

    def action_descend(self) -> None:
        """Reroot the tree at the highlighted directory."""
        tree = self.query_one(DirectoryTree)
        node = tree.cursor_node
        if node is None or node.data is None:
            self.notify("No directory highlighted", severity="warning")
            return
        path = Path(node.data.path)
        if not path.is_dir():
            self.notify("Not a directory", severity="warning")
            return
        tree.path = str(path)
        self._update_subtitle(path)

    def action_refresh_tree(self) -> None:
        self.query_one(DirectoryTree).reload()

    def action_open_claude(self) -> None:
        """Suspend the app and run the `claude` CLI in the highlighted dir."""
        tree = self.query_one(DirectoryTree)
        node = tree.cursor_node
        if node is None or node.data is None:
            self.notify("No directory highlighted", severity="warning")
            return
        target_dir = _claude_target_dir(Path(node.data.path))

        claude = shutil.which("claude")
        if claude is None:
            self.notify("`claude` CLI not found on PATH", severity="error")
            return

        with self.suspend():
            subprocess.run([claude], cwd=str(target_dir))
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


def _claude_target_dir(path: Path) -> Path:
    """Directory to open Claude in: the path itself if a dir, else its parent."""
    return path if path.is_dir() else path.parent


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
