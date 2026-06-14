"""Resource-path resolution that works both from source and when frozen.

All "am I running inside a PyInstaller bundle?" logic is confined to this
module (research R3). When run from source this is a no-op pass-through; when
frozen, bundled resources live under ``sys._MEIPASS``. The headless core does
not currently load any external runtime assets (research R4), so this helper
exists for window icons / data files that may be bundled later via the spec's
``datas=``.
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running inside a PyInstaller (or similar) bundle."""
    return getattr(sys, "frozen", False)


def resource_path(relative: str | Path) -> Path:
    """Resolve a bundled resource path.

    When frozen, resolves ``relative`` against the PyInstaller extraction
    directory (``sys._MEIPASS``). Otherwise resolves it against the package
    directory so behaviour is identical from source.
    """
    if is_frozen():
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent
    return base / Path(relative)
