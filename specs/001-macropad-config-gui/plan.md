# Implementation Plan: Macropad Configuration GUI

**Branch**: `001-macropad-config-gui` | **Date**: 2026-06-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-macropad-config-gui/spec.md`

## Summary

Build a small desktop GUI that creates and edits the YAML configuration files consumed by the existing `ch57x-keyboard-tool` CLI. The user defines the pad layout (rows, columns, knobs), clicks buttons/knobs in a visual representation to assign actions per layer, and saves a file that passes the CLI's `validate` command. Technical approach: Python 3.11+/Tkinter single-window app with a headless core (data model, `ruamel.yaml` round-trip I/O, and a Python mirror of the tool's action grammar for live validation) — see [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Tkinter/ttk (stdlib GUI), `ruamel.yaml` (round-trip YAML I/O). No other runtime dependencies.

**Storage**: Local YAML files (the ch57x-keyboard-tool configuration format); no database.

**Testing**: `pytest` for the headless core (model, YAML I/O, action validator); `ch57x-keyboard-tool/example-mapping.yaml` as golden round-trip fixture; GUI validated manually via quickstart scenarios.

**Target Platform**: Desktop — Windows 11 primary; macOS/Linux supported (same platforms as the CLI tool).

**Project Type**: Desktop app (single project) with a strictly separated headless core.

**Performance Goals**: Instant interactive feedback — action validation < 50 ms per entry; open/save of any realistic config (≤ 8×8 grid × 3 layers) < 1 s.

**Constraints**: Offline, single-user, local files only. Saved output must be byte-compatible with the CLI tool's parser (FR-013); comments/unknown fields in hand-written files preserved on round-trip (SC-003). The cloned `ch57x-keyboard-tool/` folder is read-only reference — never modified.

**Scale/Scope**: One window plus dialogs; grids up to 8×8 with 0–4 knobs and 1–3 layers; ~120 named keys, 10 media actions, 4 mouse action families in the action vocabulary.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is the unmodified template — no project principles have been ratified. **No gates to enforce; check passes by default.** (Consider running `/speckit-constitution` to establish principles.)

In lieu of a constitution, the plan self-imposes two discipline rules consistent with Spec Kit defaults: (1) headless core independent of the UI toolkit so correctness is unit-testable, (2) simplest stack that satisfies the spec (stdlib GUI, one third-party library).

**Post-design re-check (Phase 1)**: Design introduces one project, two runtime layers (core + ui), one third-party dependency. No violations; Complexity Tracking left empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-macropad-config-gui/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── yaml-config.md   # File-format + action-grammar contract with the CLI tool
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── macropad_gui/
    ├── __init__.py
    ├── __main__.py          # entry point: python -m macropad_gui
    ├── model.py             # Config, Layout, Layer, KnobBinding dataclasses + layout-resize logic
    ├── actions.py           # action vocabulary (R4) + parser/validator mirroring parse.rs
    ├── yaml_io.py           # load/save via ruamel.yaml round-trip; schema errors (R5)
    ├── cli_bridge.py        # optional: locate + invoke ch57x-keyboard-tool validate (R3)
    └── ui/
        ├── __init__.py
        ├── main_window.py   # menu, layout settings panel, layer tabs, dirty-state tracking
        ├── pad_view.py      # visual grid of buttons + knobs, selection, assignment labels
        └── action_editor.py # guided picker (modifiers/keys/media/mouse/sequence) + raw text mode

tests/
├── conftest.py              # fixtures incl. path to ch57x-keyboard-tool/example-mapping.yaml
├── test_model.py            # layout resize, layer handling, unassigned-key semantics
├── test_actions.py          # grammar: every example in doc/actions.md + invalid cases
└── test_yaml_io.py          # golden round-trip of example-mapping.yaml; error reporting

ch57x-keyboard-tool/         # existing cloned repo — read-only reference, not part of build
```

**Structure Decision**: Single project rooted at `src/macropad_gui/`. The `ui/` package is the only place Tkinter is imported; `model.py`, `actions.py`, `yaml_io.py`, and `cli_bridge.py` form the headless core covered by `tests/`. This keeps format fidelity and validation (where the spec's success criteria concentrate) fully unit-testable.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*(No violations — table intentionally empty.)*
