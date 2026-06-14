"""Single source of truth for the application version.

Reports the version from the installed package metadata (which setuptools
derives from ``pyproject.toml``) so that source-run and PyInstaller-packaged
builds always agree on one value. Falls back to a literal only when the
package metadata is unavailable (e.g. an unusual frozen layout).
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

#: Used only if package metadata cannot be read. Keep in sync with pyproject.toml.
_FALLBACK_VERSION = "0.1.0"

try:
    __version__ = _pkg_version("macropad-gui")
except PackageNotFoundError:  # pragma: no cover - exercised only without metadata
    __version__ = _FALLBACK_VERSION
