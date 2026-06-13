# Tasks: Macropad Configuration GUI

**Input**: Design documents from `specs/001-macropad-config-gui/`

**Prerequisites**: plan.md ✓ | spec.md ✓ | research.md ✓ | data-model.md ✓ | contracts/ ✓

**Tests**: Core unit tests (model, actions, YAML I/O) are included in the Foundational phase per plan.md — they cover the headless layer where success-criteria risk concentrates. No TDD gate is required; implement test and source together.

**Organization**: Phases follow user story priority (P1 → P2 → P2 → P3). The UI's Tkinter import is isolated to `src/macropad_gui/ui/`; everything else in the core is Tkinter-free.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks in same phase)
- **[Story]**: Maps to user story in spec.md (US1–US4)
- Exact file paths required in every task description

## Path Conventions

Single project at repository root:

```
src/macropad_gui/   — headless core + UI package
tests/              — pytest suite (headless core only)
```

---

## Phase 1: Setup

**Purpose**: Project initialization — layout on disk, entry point, dependencies declared.

- [X] T001 Create directory tree: `src/macropad_gui/`, `src/macropad_gui/ui/`, `tests/` at repository root
- [X] T002 Create `pyproject.toml` at repository root declaring Python 3.11+ requirement, `ruamel.yaml` runtime dependency, and `pytest` dev dependency; add `[project.scripts]` entry `macropad-gui = "macropad_gui.__main__:main"`
- [X] T003 [P] Create `src/macropad_gui/__init__.py` (empty) and `src/macropad_gui/ui/__init__.py` (empty)
- [X] T004 [P] Create `src/macropad_gui/__main__.py` entry point: `def main(): ...` stub that opens a Tk root window with title "Macropad Config GUI" and calls `mainloop()`
- [X] T005 [P] Create `tests/conftest.py` with a `example_yaml_path` pytest fixture returning the absolute path to `ch57x-keyboard-tool/example-mapping.yaml`

**Checkpoint**: `python -m macropad_gui` opens an empty window without errors; `pytest tests/` collects without import errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Headless core — data model, action grammar, YAML I/O, and their tests. **No UI story can begin until this phase is complete.**

**⚠️ CRITICAL**: Every user story phase depends on these modules being correct and tested.

- [X] T006 Implement `Layout`, `KnobBinding`, `Layer`, and `Config` dataclasses in `src/macropad_gui/model.py`; include `Config.resize(new_layout)` method that returns the set of assignments that would be lost (callers decide whether to proceed); include `dirty` flag on Config; see data-model.md for field constraints and invariants
- [X] T007 [P] Implement action vocabulary and parser in `src/macropad_gui/actions.py`: encode the full R4 vocabulary from research.md (modifiers, WellKnownCode names, media codes, mouse grammar) as constants/enums; implement `parse_action(text) -> Action` raising `ActionError(position, reason)` on invalid input; implement `serialize_action(action) -> str` (identity — returns `.text`); derive `Action.kind` as KEYBOARD_MACRO / MEDIA / MOUSE; document that unassigned positions use `<0>`
- [X] T008 [P] Implement `src/macropad_gui/yaml_io.py`: `load(path) -> Config` using `ruamel.yaml` round-trip loader — validate schema bounds from R5 (rows 1–8, columns 1–8, knobs 0–4, layers 1–3, known orientation/model values), raise `ConfigFileError` or `SchemaError` on violation; `save(config, path)` writes back into the round-trip document to preserve comments/key-order/unknown fields (SC-003), generates a clean document for new configs
- [X] T009 Implement `tests/test_model.py`: test Layout.resize() assignment-loss detection (grow keeps all, shrink reports excess), Layer unassigned None → `<0>` serialization round-trip, Config.dirty toggling, KnobBinding defaults
- [X] T010 [P] Implement `tests/test_actions.py`: parse every example action string from `ch57x-keyboard-tool/doc/actions.md`; assert correct `kind`; assert known-invalid inputs raise `ActionError` with a non-empty `reason`; cover: modifier-only accord, 5-chord sequence, `{delay(100)}` option prefix, raw HID `<101>`, all media tokens, click/wheel/move/drag with and without modifiers
- [X] T011 [P] Implement `tests/test_yaml_io.py`: golden round-trip test — load `example-mapping.yaml` (via `example_yaml_path` fixture), save to a temp file, assert byte-for-byte comment and key-order preservation; test `SchemaError` raised for `knobs: 9`; test `ConfigFileError` raised for malformed YAML

**Checkpoint**: `pytest tests/` passes green. `python -m macropad_gui` still opens without errors.

---

## Phase 3: User Story 1 — Define Pad Layout and Assign Key Mappings (Priority: P1) 🎯 MVP

**Goal**: User sets rows/columns/knobs, sees a visual grid, clicks any button or knob to assign an action, and saves a valid YAML file.

**Independent Test**: Set rows=3, columns=4, knobs=2; assign `ctrl-c` to button (1,1) and `volumeup`/`mute`/`volumedown` to knob 1; save; run `ch57x-keyboard-tool validate <file>` → exits 0. (See quickstart.md Scenario 1.)

- [X] T012 [US1] Implement `src/macropad_gui/ui/main_window.py`: create `MainWindow(tk.Tk)` class with a settings panel (rows/columns/knobs `ttk.Spinbox`, model `ttk.Combobox`, orientation `ttk.Combobox`), a central frame for the pad view, a bottom status bar, and File menu (New, Open, Save, Save As, Exit); wire `Config` as the backing model; track dirty state and update window title with asterisk
- [X] T013 [US1] Implement `src/macropad_gui/ui/pad_view.py`: `PadView(ttk.Frame)` that takes a `Config` and renders a grid of `ttk.Button` widgets (one per button position) and knob widgets (three small buttons labeled ↺ / ⏎ / ↻ per knob); each widget displays its current assignment text (truncated to fit), `(unassigned)` when None; clicking any widget calls a registered `on_select(position, kind)` callback
- [X] T014 [US1] Implement `src/macropad_gui/ui/action_editor.py`: `ActionEditor` dialog (subclass of `tk.Toplevel`) that opens with the current action text pre-filled in a `ttk.Entry`; on entry change, calls `parse_action()` and shows a red status label with `ActionError.reason` or a green "valid" label; OK is only enabled when the entry is valid or empty (empty → unassigned); Cancel discards; returns the new action text or `None`
- [X] T015 [US1] Wire settings panel changes (rows/columns/knobs) to rebuild `PadView` on value commit in `src/macropad_gui/ui/main_window.py`; new Config created with empty layers when dimensions change (no resize warning yet — that is Phase 7)
- [X] T016 [US1] Wire `PadView.on_select` → open `ActionEditor` → update `Config` assignment → refresh `PadView` label → set `config.dirty = True` in `src/macropad_gui/ui/main_window.py`
- [X] T017 [US1] Implement File → Save / Save As in `src/macropad_gui/ui/main_window.py`: call `yaml_io.save(config, path)`; on `ConfigFileError`/`SchemaError` show `tk.messagebox.showerror`; on success clear dirty flag; Save uses `config.source_path` if set, else falls back to Save As dialog
- [X] T018 [US1] Update `src/macropad_gui/__main__.py` to instantiate `MainWindow` with a fresh 3×4, 2-knob default `Config` and start the event loop

**Checkpoint**: User Story 1 is fully functional — launch → set layout → assign keys → save → `validate` passes.

---

## Phase 4: User Story 2 — Edit an Existing Configuration File (Priority: P2)

**Goal**: User opens an existing YAML config, sees all assignments, edits any, saves — comments and field order survive.

**Independent Test**: Open `ch57x-keyboard-tool/example-mapping.yaml`; verify every assignment visible in the grid matches the file; change one entry; save to a copy; diff → only that entry changed, all comments intact. (See quickstart.md Scenario 2.)

- [X] T019 [US2] Implement File → Open in `src/macropad_gui/ui/main_window.py`: call `yaml_io.load(path)` → update `self.config`; rebuild settings panel values from loaded `Config` (rows, columns, knobs, model, orientation); call `pad_view.refresh(config)` to render all assignments; clear dirty flag; handle `ConfigFileError` / `SchemaError` with `tk.messagebox.showerror` without crashing (FR-012)
- [X] T020 [US2] Add `PadView.refresh(config)` method in `src/macropad_gui/ui/pad_view.py` that destroys and redraws all button/knob widgets to match the new Config (handles layout dimension changes on open)
- [X] T021 [US2] Ensure `yaml_io.save()` writes into the `ruamel.yaml` round-trip document (not a fresh serialization) when `config.source_path` is set and the document object is cached on the Config; verify by running `test_yaml_io.py` golden round-trip test (T011) — no new test task needed

**Checkpoint**: Open example-mapping.yaml → all assignments shown → change one → save copy → diff shows single change, all comments preserved.

---

## Phase 5: User Story 3 — Multiple Layers (Priority: P2)

**Goal**: User switches between up to three independent layers, each with its own key assignments, and all layers are written to the saved file.

**Independent Test**: Assign different actions to the same position on layer 1 and layer 2; save; open the file in a text editor → both layers present with distinct assignments. (See quickstart.md Scenario 3.)

- [X] T022 [US3] Add a `ttk.Notebook` layer tab bar to `src/macropad_gui/ui/main_window.py` with 1–3 tabs labeled "Layer 1", "Layer 2", "Layer 3"; the number of tabs matches a "Layers" spinbox (default 3); switching tabs calls `pad_view.refresh(config.layers[i])`; new layers are initialized with all-None assignments
- [X] T023 [US3] Update `Config.resize()` in `src/macropad_gui/model.py` to propagate resizing across all layers (not just the active one) and aggregate assignment-loss across all layers for the confirmation check (Phase 7)
- [X] T024 [US3] Update `yaml_io.save()` in `src/macropad_gui/yaml_io.py` to write all `config.layers` in order to the YAML `layers:` list; each layer's `buttons` grid respects orientation transposition per the contract (contracts/yaml-config.md); unassigned positions written as `<0>`
- [X] T025 [US3] Update `yaml_io.load()` in `src/macropad_gui/yaml_io.py` to populate all layers from the file; set the layer tab count spinner to match the loaded layer count; select layer 1 tab

**Checkpoint**: All three layers independently assignable, saved, and loaded correctly.

---

## Phase 6: User Story 4 — Guided Action Picker with Validation (Priority: P3)

**Goal**: User can compose actions through a guided UI (modifier checkboxes, key dropdown, media list, mouse params) without knowing the syntax; invalid raw-text entries are flagged inline; Save is blocked until all entries are valid.

**Independent Test**: Build `ctrl-shift-a` through the guided picker → OK → assignment shows `ctrl-shift-a`. Enter `ctrl-bogus` in raw-text mode → red error label names `bogus` as unknown → Save disabled. (See quickstart.md Scenario 4.)

- [X] T026 [US4] Extend `ActionEditor` in `src/macropad_gui/ui/action_editor.py` with a `ttk.Notebook` inside the dialog: tab "Keyboard" (modifier checkboxes for ctrl/shift/alt/win and aliases, key `ttk.Combobox` populated from `actions.WELL_KNOWN_KEYS`, raw-HID `ttk.Entry` for `<N>`), tab "Media" (listbox of all 10 media tokens), tab "Mouse" (action-type combobox: click/wheel/move/drag; button checkboxes; numeric spinboxes for x/y/n); switching tabs generates the corresponding action text into the raw-text field
- [X] T027 [US4] Add sequence builder in the Keyboard tab of `src/macropad_gui/ui/action_editor.py`: an ordered list of up to 5 chords (each built with the modifier + key controls), "Add chord" / "Remove last" buttons, and a `{delay(ms)}` options prefix spinbox; assembles the full `{options}accord,accord,...` string
- [X] T028 [US4] Wire real-time validation in `ActionEditor` raw-text entry: bind `<KeyRelease>` to call `parse_action(text)` and update the status label (red + reason on `ActionError`, green "valid" otherwise); disable OK button while invalid in `src/macropad_gui/ui/action_editor.py`
- [X] T029 [US4] Block File → Save / Save As in `src/macropad_gui/ui/main_window.py` when `config` contains any `ActionError`-flagged assignment; show a summary dialog listing which positions are invalid; positions are flagged at assignment time and stored as a separate `errors` dict on Config

**Checkpoint**: User Story 4 fully functional — guided picker composes valid action strings; invalid entries caught inline; Save blocked until resolved.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Safety guards, optional CLI integration, edge-case UX, and final manual validation.

- [X] T030 Add layout-resize confirmation dialog in `src/macropad_gui/ui/main_window.py`: before applying a dimension decrease, call `config.resize()` to get the would-be-lost set; if non-empty, show `tk.messagebox.askyesno` listing how many assignments across which layers would be discarded; cancel restores previous spinbox values
- [X] T031 Add WM_DELETE_WINDOW handler in `src/macropad_gui/ui/main_window.py`: if `config.dirty` is True, show save/discard/cancel prompt (`tk.messagebox.askyesnocancel`) before closing (FR-011)
- [X] T032 [P] Implement `src/macropad_gui/cli_bridge.py`: `find_tool() -> Path | None` searches PATH and a user-configurable setting for a `ch57x-keyboard-tool` binary; `validate(config_path, tool_path) -> (bool, str)` invokes the binary's `validate` subcommand and returns success + stdout/stderr
- [X] T033 [P] Add Tools → "Validate with CLI Tool" menu item in `src/macropad_gui/ui/main_window.py` that saves to a temp file, calls `cli_bridge.validate()`, and shows the result in a dialog; menu item disabled if `cli_bridge.find_tool()` returns None
- [X] T034 [P] Add a 3×1-pad modifier warning: in `PadView` or `ActionEditor`, when `config.layout` is 3 rows × 1 column with 1 knob (the known-limited variant per README), display an informational label noting that modifiers are only supported on the first chord of a sequence (FR-008, contracts/yaml-config.md semantic rules); no save block
- [X] T035 Run all four quickstart.md scenarios manually and confirm each passes; fix any discrepancy found

**Checkpoint**: Full feature complete — all user stories independently functional, safety guards in place, optional CLI validation available.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Requires Phase 1 — **blocks all UI stories**
- **Phase 3 (US1 — MVP)**: Requires Phase 2 complete
- **Phase 4 (US2)**: Requires Phase 3 complete (opens files into the editor built in US1)
- **Phase 5 (US3)**: Requires Phase 3 complete (adds layer tabs to the main window from US1); can run in parallel with Phase 4
- **Phase 6 (US4)**: Requires Phase 3 complete (extends ActionEditor from US1); can run after US1 regardless of US2/US3 status
- **Phase 7 (Polish)**: Requires all desired user stories complete

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational (Phase 2) only — no story prerequisites
- **US2 (P2)**: Depends on US1 (opens files into US1's editor)
- **US3 (P2)**: Depends on US1 (extends US1's main window); independent of US2
- **US4 (P3)**: Depends on US1 (extends US1's ActionEditor); independent of US2/US3

### Within Each Phase

- [P]-marked tasks touch different files and can run concurrently
- Non-[P] tasks within a phase must run in listed order

---

## Parallel Examples

### Phase 2 (Foundational) — parallelizable tasks

```
Concurrent batch 1 (all independent files):
  T007 — actions.py (vocabulary + parser)
  T008 — yaml_io.py (load/save)
  T010 — test_actions.py
  T011 — test_yaml_io.py

Sequential after T007, T008:
  T006 — model.py (depends on action.py types)
  T009 — test_model.py (depends on model.py)
```

### Phase 3 (US1 MVP) — within-story order

```
Sequential (each builds on previous):
  T012 — main_window.py skeleton
  T013 — pad_view.py (needs window frame to attach to)
  T014 — action_editor.py (standalone dialog)
  T015 — wire settings → PadView rebuild
  T016 — wire click → ActionEditor → assignment update
  T017 — wire File → Save/Save As
  T018 — update __main__.py to launch MainWindow
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T005)
2. Complete Phase 2: Foundational (T006–T011) — all tests must pass
3. Complete Phase 3: User Story 1 (T012–T018)
4. **STOP and VALIDATE**: run quickstart.md Scenario 1 manually
5. Deliverable: a working single-layer pad editor that saves valid YAML

### Incremental Delivery

1. Setup + Foundational → headless core with test coverage
2. US1 → visual editor MVP (save valid files from scratch)
3. US2 → round-trip editing of existing hand-written configs
4. US3 → full three-layer support
5. US4 → guided picker + inline validation (no more manual syntax)
6. Polish → resize guards, unsaved-changes prompt, optional CLI validate

---

## Notes

- No TDD gate required — implement test and source together within each phase
- `<0>` (HID no-op) is the canonical serialized form of an unassigned position; the GUI displays it as `(unassigned)`
- Raw HID codes (`<N>`), delay options (`{delay(100)}`), and any action the picker cannot compose remain editable as raw text and are never corrupted on save
- `ch57x-keyboard-tool/` is read-only reference — never modify it
- Comments, YAML key order, and unknown fields in hand-written configs are preserved by `ruamel.yaml` round-trip mode; `test_yaml_io.py` (T011) is the regression tripwire for this guarantee
- Each phase checkpoint is independently demonstrable to the user
