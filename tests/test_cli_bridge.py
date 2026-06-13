"""cli_bridge tests using a fake ch57x-keyboard-tool executable.

The fake records the subcommand it was called with and exits 0 (or
non-zero when the config name contains "bad"), so we can assert that
validate/upload invoke the right subcommand and surface output without
needing the real Rust binary or a USB device.
"""

import sys
import textwrap
from pathlib import Path

import pytest

from macropad_gui import cli_bridge


@pytest.fixture
def fake_tool(tmp_path: Path) -> Path:
    """A stand-in binary: a Python script wrapped in a platform launcher."""
    script = tmp_path / "tool.py"
    script.write_text(textwrap.dedent("""
        import sys
        sub = sys.argv[1] if len(sys.argv) > 1 else ""
        cfg = sys.argv[2] if len(sys.argv) > 2 else ""
        print(f"ran {sub} on {cfg}")
        sys.exit(1 if "bad" in cfg else 0)
    """))
    if sys.platform == "win32":
        launcher = tmp_path / "ch57x-keyboard-tool.bat"
        launcher.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n')
    else:
        launcher = tmp_path / "ch57x-keyboard-tool"
        launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n')
        launcher.chmod(0o755)
    return launcher


def test_find_tool_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_bridge.shutil, "which", lambda _name: None)
    monkeypatch.setattr(cli_bridge, "_LOCAL_CANDIDATES", (tmp_path,))
    assert cli_bridge.find_tool() is None


def test_find_tool_configured_path(fake_tool):
    assert cli_bridge.find_tool(fake_tool) == fake_tool


def test_validate_passes(fake_tool, tmp_path):
    cfg = tmp_path / "ok.yaml"
    cfg.write_text("x")
    passed, output = cli_bridge.validate(cfg, fake_tool)
    assert passed
    assert "ran validate" in output


def test_validate_fails(fake_tool, tmp_path):
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("x")
    passed, output = cli_bridge.validate(cfg, fake_tool)
    assert not passed
    assert "ran validate" in output


def test_upload_calls_upload_subcommand(fake_tool, tmp_path):
    cfg = tmp_path / "ok.yaml"
    cfg.write_text("x")
    succeeded, output = cli_bridge.upload(cfg, fake_tool)
    assert succeeded
    assert "ran upload" in output


def test_upload_reports_failure(fake_tool, tmp_path):
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("x")
    succeeded, output = cli_bridge.upload(cfg, fake_tool)
    assert not succeeded
    assert "ran upload" in output


def test_run_handles_missing_binary(tmp_path):
    succeeded, output = cli_bridge.upload(tmp_path / "c.yaml",
                                          tmp_path / "nonexistent-binary")
    assert not succeeded
    assert "could not run" in output
