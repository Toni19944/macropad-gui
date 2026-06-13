# Research: Macropad Configuration GUI

**Feature**: 001-macropad-config-gui | **Date**: 2026-06-13

All Technical Context unknowns are resolved below. Sources: `ch57x-keyboard-tool/` repository (README.md, example-mapping.yaml, doc/actions.md, src/config.rs, src/parse.rs, src/keyboard/mod.rs).

## R1: GUI technology

**Decision**: Python 3.11+ with Tkinter (standard library) + ttk widgets.

**Rationale**:
- The feature is a small, local, single-window desktop form: a settings panel, a grid of clickable buttons, layer tabs, and dialogs. Tkinter handles all of this with zero third-party UI dependencies.
- Cross-platform out of the box (Windows primary, macOS/Linux supported), matching where the CLI tool runs.
- "Simple GUI" is the explicit user goal; fastest path to a working, maintainable tool.
- No build/packaging toolchain required to run from source (`python -m macropad_gui`).

**Alternatives considered**:
- **Rust + egui/iced**: same language as the cloned tool, but the GUI is a separate program that only shares a *file format* with it, not code. Rust GUI iteration is slower and overkill for a form-based app.
- **Tauri/Electron (web stack)**: best-looking option but adds a large toolchain (Node, bundlers) for a tool that writes a small YAML file. Rejected for complexity.
- **PySide6/Qt**: nicer widgets than Tkinter but a ~700 MB toolchain dependency; not justified for this scope. Can be revisited later without changing the model layer.

## R2: YAML read/write library

**Decision**: `ruamel.yaml` (round-trip mode).

**Rationale**:
- The spec's edge cases require opening hand-written files and not corrupting what the GUI doesn't model. `ruamel.yaml` round-trip mode preserves comments, key order, and unknown fields on load → save, which directly satisfies SC-003 (zero data loss on round-trip) and keeps hand-written files pleasant.
- Actively maintained, pure-Python install.

**Alternatives considered**:
- **PyYAML**: simpler and more common, but discards comments and ordering on save — hand-edited configs (like the heavily commented example file) would be flattened. Rejected because editing existing files is a P2 story.

## R3: Action validation strategy

**Decision**: Re-implement the action grammar in Python as a validator/parser, mirroring `src/parse.rs`, and additionally offer optional "validate with CLI tool" integration when a `ch57x-keyboard-tool` binary is found on PATH or configured.

**Rationale**:
- FR-009/SC-005 require flagging invalid entries *as the user types/saves*, which needs in-process validation; shelling out per keystroke is not viable.
- The grammar is small and fully visible in `parse.rs`; the vocabulary is enumerable (see R4). A Python mirror is straightforward and unit-testable against examples from `doc/actions.md` and `example-mapping.yaml`.
- The CLI `validate` pass remains the authoritative final check (FR-013); the optional integration gives users one-click certainty without making the binary a hard dependency.

**Alternatives considered**:
- **Always shell out to `ch57x-keyboard-tool validate`**: authoritative but requires the binary, is file-granular (poor per-field error messages), and slow for interactive feedback. Kept only as an optional final check.
- **No validation, free text only**: fails FR-009. Rejected.

## R4: Action vocabulary (extracted from tool source — ground truth for the validator)

**Decision**: Encode the following vocabulary, taken from `src/keyboard/mod.rs` and `src/parse.rs`:

- **Modifiers** (keyboard): `ctrl`, `shift`, `alt`/`opt`, `win`/`cmd`, `rctrl`, `rshift`, `ralt`/`ropt`, `rwin`/`rcmd` (case-insensitive).
- **Keys (WellKnownCode)**: `a`–`z`, `0`–`9`, `enter`, `escape`, `backspace`, `tab`, `space`, `minus`, `equal`, `leftbracket`, `rightbracket`, `backslash`, `nonushash`, `semicolon`, `quote`, `grave`, `comma`, `dot`, `slash`, `capslock`, `f1`–`f24`, `printscreen`, `scrolllock`/`macbrightnessdown`, `pause`/`macbrightnessup`, `insert`, `home`, `pageup`, `delete`, `end`, `pagedown`, `right`, `left`, `down`, `up`, `numlock`, `numpadslash`, `numpadasterisk`, `numpadminus`, `numpadplus`, `numpadenter`, `numpad0`–`numpad9`, `numpaddot`, `nonusbackslash`, `application`, `power`, `numpadequal`.
- **Custom HID codes**: `<N>` where N is 0–255 decimal.
- **Accord**: `[mod-]*[key]` — modifiers joined to an optional key with `-` (modifier-only accords like `alt-shift` are legal).
- **Keyboard macro**: optional `{delay(ms)}` options prefix, then 1–5 comma-separated accords.
- **Media codes** (cannot mix with modifiers/keys): `next`, `previous`/`prev`, `stop`, `play`, `mute`, `volumeup`, `volumedown`, `favorites`, `calculator`, `screenlock`.
- **Mouse events**: buttons `left`, `right`, `middle` (combinable with `+`); `click(buttons)` with aliases `click`/`lclick` (left), `rclick` (right), `mclick` (middle); `wheel(±n)` with aliases `wheelup`, `wheeldown`; `move(x,y)`; `drag(buttons,x,y)`; x/y/n in −128…127. Optional mouse modifier prefix limited to `ctrl`, `shift`, `alt`.

**Rationale**: Mirroring the exact enums guarantees GUI validation agrees with the tool's parser.

## R5: Configuration file schema bounds

**Decision**: Schema fields and bounds for the GUI:
- `model` (optional): one of `ch57x-1`, `ch57x-2`, `ch57x-3` (serde kebab-case of `KeyboardModel`); GUI also allows leaving it unset.
- `orientation`: `normal` | `upsidedown` | `clockwise` | `counterclockwise`.
- `rows`, `columns`: 1–8 (GUI bound; known hardware tops out at 5×3, kept slightly loose for unknown variants).
- `knobs`: 0–4 (known hardware: 0–3).
- `layers`: 1–3 ordered layers; each layer has `buttons` (rows×columns grid of action strings, transposed when orientation is vertical) and `knobs` (list of `{ccw, press, cw}`).

**Rationale**: Matches `src/config.rs` deserialization; bounds follow spec assumptions ("up to roughly 5 rows/columns and 0–3 knobs", "layers capped at three") with one step of headroom on grid size.

**Alternatives considered**: Unbounded dimensions — rejected; the GUI should stop obviously-wrong input early (FR-009) and the tool's own grid checks would fail later anyway.

## R6: Unassigned-key representation

**Decision**: Buttons left unassigned in the GUI are written as `<0>` (custom HID code 0 = "Reserved / no event" in the HID usage table). The empty string is rejected by the tool's parser, but `<0>` parses as a valid accord (`parse.rs` accepts `<N>` for any 0–255) and emits no keypress.

**Rationale**: Satisfies the edge case "unassigned keys must still produce a valid file". The GUI displays such keys as "(unassigned)" and writes `<0>` on save; on load, `<0>` is shown as unassigned.

**Alternatives considered**: Prompting the user to fill every key before save — rejected as hostile for large pads; refusing to save — fails the edge-case requirement.

## R7: Testing approach

**Decision**: `pytest` for the non-UI core (model, YAML I/O, action validator) with `example-mapping.yaml` as a golden round-trip fixture. UI is exercised manually via quickstart scenarios; UI logic is kept thin so the core carries the correctness burden.

**Rationale**: The risk concentrates in format fidelity and validation, both headless-testable. Automated GUI testing of Tkinter adds little for a single-window form.

## R8: Distribution

**Decision**: Run from source (`python -m macropad_gui`) for this feature; packaging (PyInstaller single-file exe) is deferred and noted as future work.

**Rationale**: Out of the spec's scope; the user is the developer-operator on Windows with Python available.
