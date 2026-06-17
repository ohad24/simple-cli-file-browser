"""Unit tests for the _resolve_start_path helper."""

from pathlib import Path

import pytest

from file_browser.browser import _resolve_start_path


def test_defaults_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert _resolve_start_path(["prog"]) == tmp_path.resolve()


def test_returns_given_directory(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    assert _resolve_start_path(["prog", str(sub)]) == sub.resolve()


def test_file_arg_collapses_to_parent(tmp_path):
    file_path = tmp_path / "note.txt"
    file_path.write_text("hello")
    assert _resolve_start_path(["prog", str(file_path)]) == tmp_path.resolve()


def test_expands_user(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert _resolve_start_path(["prog", "~"]) == tmp_path.resolve()


def test_missing_path_raises_system_exit(tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(SystemExit):
        _resolve_start_path(["prog", str(missing)])
