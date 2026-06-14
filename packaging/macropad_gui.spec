# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the self-contained Windows macropad-gui executable.

Builds a single, windowed (no-console) ``.exe`` from the existing
``macropad_gui`` entry point. Run via the committed wrapper:

    ./packaging/build_windows.ps1

or directly:

    pyinstaller packaging/macropad_gui.spec --noconfirm --clean

Design notes (see specs/002-single-exe-packaging/):
- onefile + windowed: exactly one self-contained file, no console (FR-001,
  FR-003, FR-006, SC-006).
- datas=[]: the app loads no external runtime assets (research R4 / T006 audit).
- version='version_info.txt': embeds the app name + version into the binary's
  Windows file properties (FR-010, US4).
- The additive ``_version`` and ``_paths`` helpers are pulled in automatically
  as part of the ``macropad_gui`` package; they are listed under hiddenimports
  defensively so they are always present even though they are imported lazily.
"""

import os

# __file__ is not defined when a .spec is exec'd by PyInstaller; SPECPATH is.
_spec_dir = SPECPATH  # noqa: F821 - injected by PyInstaller
_repo_root = os.path.abspath(os.path.join(_spec_dir, os.pardir))
# Analyze the packaging shim, not src/macropad_gui/__main__.py directly: the
# shim imports the package absolutely so the entry module keeps its package
# context (relative imports work). See packaging/entrypoint.py.
_entry_point = os.path.join(_spec_dir, "entrypoint.py")
_version_resource = os.path.join(_spec_dir, "version_info.txt")


a = Analysis(
    [_entry_point],
    pathex=[os.path.join(_repo_root, "src")],
    binaries=[],
    datas=[],
    hiddenimports=[
        "macropad_gui._version",
        "macropad_gui._paths",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="macropad-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=_version_resource,
)
