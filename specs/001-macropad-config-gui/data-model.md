# Data Model: Macropad Configuration GUI

**Feature**: 001-macropad-config-gui | **Date**: 2026-06-13

Entities live in the headless core (`src/macropad_gui/model.py`, `actions.py`). The YAML mapping is defined in [contracts/yaml-config.md](contracts/yaml-config.md).

## Entity: Config

The root object; corresponds one-to-one with a YAML configuration file.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `model` | str \| None | `ch57x-1` \| `ch57x-2` \| `ch57x-3` \| None | Optional in the tool's schema |
| `orientation` | str | `normal` \| `upsidedown` \| `clockwise` \| `counterclockwise` | Default `normal` |
| `layout` | Layout | — | rows/columns/knobs |
| `layers` | list[Layer] | 1–3 entries, ordered | Common hardware has exactly 3 |
| `source_path` | Path \| None | — | Where it was loaded from; None for new configs |
| `dirty` | bool | — | Unsaved-changes flag (FR-011) |

**Invariant**: every Layer's grid dimensions and knob count always match `layout`. Enforced by Config methods; Layers are never resized directly.

## Entity: Layout

| Field | Type | Constraints |
|---|---|---|
| `rows` | int | 1–8 |
| `columns` | int | 1–8 |
| `knobs` | int | 0–4 |

**State transition — resize** (FR-011, edge case "shrinking layout"):
`Config.resize(new_layout)` computes the set of non-empty assignments that fall outside the new bounds across all layers. If non-empty, the caller (UI) must confirm with the user before the resize proceeds; assignments inside the new bounds are preserved, those outside are discarded. Growing never discards.

## Entity: Layer

One complete set of assignments.

| Field | Type | Constraints |
|---|---|---|
| `buttons` | list[list[Action \| None]] | `rows` lists of `columns` entries |
| `knobs` | list[KnobBinding] | exactly `layout.knobs` entries |

`None` = unassigned. Serialized as `<0>` (no-op HID code) on save; `<0>` deserializes back to unassigned (research R6).

## Entity: KnobBinding

| Field | Type | Constraints |
|---|---|---|
| `ccw` | Action \| None | counter-clockwise rotation |
| `press` | Action \| None | knob push |
| `cw` | Action \| None | clockwise rotation |

## Value object: Action

An immutable validated wrapper around the tool's action string (e.g. `ctrl-shift-a`, `play`, `click(left+right)`, `{delay(100)}ctrl-a,ctrl-c`, `<101>`).

| Field | Type | Notes |
|---|---|---|
| `text` | str | Exact string written to YAML — preserved verbatim |
| `kind` | enum | `KEYBOARD_MACRO` \| `MEDIA` \| `MOUSE` (derived by parser) |

**Validation rules** (mirror of `parse.rs`, full grammar in the contract):
- Parses against the grammar in [contracts/yaml-config.md](contracts/yaml-config.md) → valid, with `kind` derived.
- Keyboard macros: 1–5 accords; each accord = 0+ known modifiers + optional key (named or `<0–255>`); optional leading `{delay(ms)}`.
- Media actions: single token from the media list; no modifiers, not mixable with keys.
- Mouse actions: click/move/drag/wheel forms; only `ctrl`/`shift`/`alt` modifiers; numeric args in −128…127.
- Invalid input → structured `ActionError(position, reason)` for UI display (FR-009, SC-005).

**Guided-picker coverage**: the picker composes accords, sequences, media, and common mouse actions. Anything it can't model (raw HID codes, delay options, exotic combinations) remains editable as raw text and is stored verbatim (FR-008).

## Round-trip document state (yaml_io)

To satisfy SC-003 (zero loss on open → save), `yaml_io` keeps the `ruamel.yaml` document object of a loaded file and writes edits back into it, rather than regenerating from scratch. Comments, key order, and unknown extra fields survive. New files are generated from a clean template mirroring `example-mapping.yaml`'s field order.

## Error types

| Error | Raised when | UI behavior |
|---|---|---|
| `ConfigFileError(message, line?)` | YAML unparseable / wrong structure | Error dialog, file not opened (FR-012) |
| `SchemaError(field, value, allowed)` | Values outside R5 bounds (e.g. `knobs: 9`) | Error dialog naming the field (FR-012) |
| `ActionError(position, reason)` | Action string fails grammar | Inline marker in editor; save blocked until fixed (FR-009) |
