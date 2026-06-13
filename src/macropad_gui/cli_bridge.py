"""Optional integration with the ch57x-keyboard-tool CLI binary.

The binary is never a hard dependency: the GUI's own parser mirrors the
tool's grammar.  When a binary can be found, ``validate`` offers the
authoritative final check (research R3).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_TOOL_NAME = "ch57x-keyboard-tool"

#: Repo-local cargo build outputs, tried after PATH.
_LOCAL_CANDIDATES = (
    Path(__file__).resolve().parents[2] / _TOOL_NAME / "target" / "release",
    Path(__file__).resolve().parents[2] / _TOOL_NAME / "target" / "debug",
)


def find_tool(configured: str | Path | None = None) -> Path | None:
    """Locate a ch57x-keyboard-tool binary; None when unavailable."""
    if configured:
        path = Path(configured)
        if path.is_file():
            return path
    found = shutil.which(_TOOL_NAME)
    if found:
        return Path(found)
    exe = _TOOL_NAME + (".exe" if sys.platform == "win32" else "")
    for directory in _LOCAL_CANDIDATES:
        candidate = directory / exe
        if candidate.is_file():
            return candidate
    return None


def _run(tool_path: str | Path, subcommand: str, config_path: str | Path,
         timeout: int) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [str(tool_path), subcommand, str(config_path)],
            capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"could not run {tool_path}: {e}"
    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        return True, output
    return False, output or f"{subcommand} exited with code {result.returncode}"


def validate(config_path: str | Path, tool_path: str | Path) -> tuple[bool, str]:
    """Run ``<tool> validate <config>``; returns (passed, output)."""
    passed, output = _run(tool_path, "validate", config_path, timeout=30)
    if passed and not output:
        output = "Config is valid."
    return passed, output


def upload(config_path: str | Path, tool_path: str | Path) -> tuple[bool, str]:
    """Run ``<tool> upload <config>`` to program the connected device.

    Returns (succeeded, output).  Talks to the physical macropad over
    USB, so it needs the device plugged in and the libusb/WinUSB driver
    installed; failures (no device, driver missing) surface in ``output``.
    """
    passed, output = _run(tool_path, "upload", config_path, timeout=60)
    if passed and not output:
        output = "Configuration uploaded to device."
    return passed, output
