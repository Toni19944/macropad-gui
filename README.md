# Macropad Config GUI

A small desktop GUI for creating and editing the YAML configuration files
used by [`ch57x-keyboard-tool`](https://github.com/kriomant/ch57x-keyboard-tool) —
the command-line configurator for the cheap CH57x AliExpress macropads
(the ones with a grid of keys and one or more knobs).

Instead of hand-writing YAML, you set your pad's layout (rows, columns,
knobs), click any button or knob in a visual grid to assign an action,
manage up to three layers, and save a file the tool accepts. A guided
picker builds the action strings for you (modifiers, keys, sequences,
mouse actions, media keys) and validates every entry as you type.

If you have the `ch57x-keyboard-tool` binary installed, the GUI can also
**validate** and **upload** your configuration to the device directly,
without leaving the app.

![Macropad Config GUI](preview.png)

## Features

- Visual pad editor — set rows (1–8), columns (1–8), knobs (0–4); click
  to assign.
- Up to **3 layers**, each independently editable.
- **Guided action picker** with live validation: keyboard chords and
  sequences, mouse click/move/drag/wheel, and media keys — or type raw
  action strings directly.
- Opens existing hand-written configs and **preserves comments, key
  order, and unknown fields** byte-for-byte on save.
- Safety guards: warns before a layout shrink discards assignments, and
  prompts on close with unsaved changes.
- Optional one-click **Validate** and **Upload to Device** via the
  `ch57x-keyboard-tool` binary.

## Requirements

| Dependency | Required for | Where to get it |
|---|---|---|
| **Python 3.11+** (with Tkinter) | Running the GUI | <https://www.python.org/downloads/> — on Windows, Tkinter is included by default |
| **`ruamel.yaml`** | YAML round-trip I/O | Installed automatically (see below) |
| **`ch57x-keyboard-tool`** | Validating / uploading configs to the device | <https://github.com/kriomant/ch57x-keyboard-tool> |
| **UsbDk** (Windows only) | Letting the tool talk to the macropad over USB | <https://github.com/daynix/UsbDk> |

The GUI itself only needs Python + `ruamel.yaml`; it can create and edit
valid config files with nothing else installed. The `ch57x-keyboard-tool`
binary and **UsbDk** are only needed if you want the in-app **Upload to
Device** / **Validate** buttons to work. On Windows, uploading requires
the [UsbDk](https://github.com/daynix/UsbDk) driver — install it before
trying to upload, otherwise the tool cannot open the device.

## Download (Windows `.exe`)

If you just want to run the tool on Windows without installing Python, grab
the self-contained `macropad-gui.exe` from the
[Releases](https://github.com/Toni19944/macropad-gui/releases) page and
double-click it — no Python, no dependencies, no install steps. It is a single
windowed app; the `ch57x-keyboard-tool` binary and **UsbDk** are still only
needed for the optional **Validate** / **Upload to Device** features.

The `.exe` is an **optional convenience build**. Running from source (below) is
the primary, canonical way to use the project and is fully supported on
Windows, macOS, and Linux. The `.exe` is released under the same GPLv3 license;
the [LICENSE](LICENSE) text is conveyed with each release and the corresponding
source is this public repository.

## Installation (from source — all platforms)

Running from source is the canonical path and works on **Windows, macOS, and
Linux**. Clone the repository and install the package (this pulls in
`ruamel.yaml`); a virtual environment is recommended:

```bash
git clone https://github.com/Toni19944/macropad-gui.git
cd macropad-gui

python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

python -m pip install -e .
```

## Running

```bash
python -m macropad_gui
```

On Windows you can also double-click `launch_macropad_gui.bat`. Packaging is
never required to run the app — the `.exe` is only a convenience.

## Usage

1. Set **rows**, **columns**, and **knobs** to match your pad; the grid
   redraws to match.
2. Click any button (or a knob's ↺ / ⏎ / ↻) to open the action editor.
   Compose an action with the guided tabs, or type a raw action string —
   it's validated live.
3. Use the **Layer 1/2/3** tabs to give each layer its own mappings.
4. **File → Save** writes a `.yaml` file `ch57x-keyboard-tool` accepts.
5. With the tool installed, **⬆ Upload to Device** (or **Tools → Upload
   to Device**) programs the currently shown configuration onto the
   connected macropad.

For the full action syntax (key names, modifiers, sequences, mouse and
media actions), see the upstream
[`doc/actions.md`](https://github.com/kriomant/ch57x-keyboard-tool/blob/master/doc/actions.md).

### Where the GUI looks for the tool binary

The **Validate** / **Upload** features are enabled only when a
`ch57x-keyboard-tool` binary is found. The GUI searches, in order:

1. Anywhere on your `PATH`
2. `ch57x-keyboard-tool/target/release/`
3. `ch57x-keyboard-tool/target/debug/`

The simplest setup is to put the binary on your `PATH`. Alternatively,
clone and build the tool inside this folder so the `target/` paths match.

## Development

```bash
python -m pip install -e ".[dev]"     # installs pytest + pyinstaller
pytest                                # headless core suite (Windows/macOS/Linux)
```

GitHub Actions runs `pip install -e .[dev]` + `pytest` on macOS and Linux for
every push and pull request (`.github/workflows/ci.yml`).

The codebase keeps a strict split:

- `src/macropad_gui/` — headless core (`model.py`, `actions.py`,
  `yaml_io.py`, `cli_bridge.py`), no GUI imports, fully unit-tested.
- `src/macropad_gui/ui/` — the only place Tkinter is imported.
- `tests/` — pytest suite. `tests/fixtures/example-mapping.yaml` is a
  vendored copy of the upstream example, used as the golden round-trip
  fixture so the suite needs no external checkout.

## Building the Windows `.exe`

The standalone Windows executable is built with
[PyInstaller](https://pyinstaller.org/) from a committed spec. On a Windows
host with the dev dependencies installed (`pip install -e .[dev]`), run the one
documented command from the repo root:

```powershell
./packaging/build_windows.ps1
```

This produces a single self-contained `dist/macropad-gui.exe` (no loose files
needed beside it) with the application name and version embedded in its file
properties. Re-running after editing the source rebuilds the `.exe` with no
reconfiguration. The build definition lives in `packaging/`
(`macropad_gui.spec`, `version_info.txt`, `build_windows.ps1`); `dist/` and
`build/` are gitignored. Building is Windows-only and never modifies `src/`,
`tests/`, or the `ch57x-keyboard-tool/` reference clone.

## Roadmap

- Verify and smooth out **macOS/Linux** usage (currently Windows-tested only);
  CI already exercises the core suite on both.

## License

Released under the **GNU General Public License v3.0 or later** — see
[LICENSE](LICENSE).

The distributed Windows `.exe` is covered by the same license. Each release
conveys the full [LICENSE](LICENSE) text alongside the binary (as a release
asset and/or in the release notes), and the complete corresponding source is
this public repository — satisfying GPLv3's conveyance terms for the bundled
build.

## Acknowledgements

This is a front-end for
[kriomant/ch57x-keyboard-tool](https://github.com/kriomant/ch57x-keyboard-tool);
all device communication and the configuration format are defined by that
project. USB access on Windows is provided by
[Daynix/UsbDk](https://github.com/daynix/UsbDk).
