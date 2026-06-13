# Quickstart: Macropad Configuration GUI

**Feature**: 001-macropad-config-gui

Validation/run guide. Format details: [contracts/yaml-config.md](contracts/yaml-config.md) · entities: [data-model.md](data-model.md).

## Prerequisites

- Python 3.11+ on PATH (`python --version`)
- `pip install ruamel.yaml pytest`
- Optional (for authoritative validation): a `ch57x-keyboard-tool` binary — prebuilt release or `cargo build --release` inside `ch57x-keyboard-tool/`

## Run the app

```powershell
cd D:\Programs\Tools\macropad-gui
python -m macropad_gui          # requires src/ on path or `pip install -e .`
```

## Automated checks

```powershell
pytest tests/
```

Expected: all green. Key suites — `test_actions.py` (every example from `ch57x-keyboard-tool/doc/actions.md` parses; known-bad strings rejected), `test_yaml_io.py` (golden round-trip of `ch57x-keyboard-tool/example-mapping.yaml` preserves comments/order/fields), `test_model.py` (resize warnings, unassigned `<0>` semantics).

## Scenario 1 — Create a config from scratch (User Story 1, SC-001/SC-002)

1. Launch the app. Set rows=3, columns=4, knobs=2 → grid redraws as 3×4 + 2 knobs.
2. Click button (1,1) → action editor opens. Pick `ctrl` + `c` in the guided picker → button shows `ctrl-c`.
3. Click knob 1 → assign ccw=`volumedown`, press=`mute`, cw=`volumeup`.
4. Save as `my-config.yaml`.
5. Verify: `ch57x-keyboard-tool validate my-config.yaml` (or use the app's Validate menu item if a binary is configured) → exits 0.

## Scenario 2 — Edit an existing file (User Story 2, SC-003/SC-004)

1. Open `ch57x-keyboard-tool/example-mapping.yaml` (File → Open). Every button/knob shows the assignment from the file, including `<100>` and sequences like `alt-ctrl,ctrl-b` (raw-text entries).
2. Change one button, save to a copy, and diff against the original → only that assignment changed; comments and field order intact.
3. Open a deliberately broken file (e.g. `knobs: 9`) → error dialog names the offending field; app does not crash.

## Scenario 3 — Layers (User Story 3)

1. Switch to layer 2 via the layer tabs; assign a different action to the same position as layer 1.
2. Save → file contains both layers in order; layer 3 cells saved as `<0>` placeholders.

## Scenario 4 — Validation (User Story 4, SC-005)

1. In the action editor, switch to raw text and type `ctrl-bogus` → inline error identifies `bogus` as an unknown key; Save is blocked.
2. Type `{delay(100)}ctrl-a,ctrl-c` → accepted and preserved verbatim.
3. Shrink the layout from 3×4 to 3×2 with assignments in columns 3–4 → confirmation dialog warns which assignments will be lost; cancel keeps them.
4. Close the app with unsaved changes → save/discard/cancel prompt appears.
