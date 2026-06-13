# Feature Specification: Macropad Configuration GUI

**Feature Branch**: `001-macropad-config-gui`

**Created**: 2026-06-13

**Status**: Draft

**Input**: User description: "Study the contents of "ch57x-keyboard-tool" folder. That is a cloned repo of a configurator tool made for cheap AliExpress macropads. The goal of this project is to create a GUI for the configurator. The way the configurator works now is: user edits .yaml file with their desired keyboard inputs -- User then loads the .yaml via command line. I want to make that .yaml file creation/editing easier, but adding a simple GUI that creates that file for me. It needs to have options to change the layout of the pad (rows, columns, knobs) and an easy way to set and reconfigure the key mappings."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Pad Layout and Assign Key Mappings Visually (Priority: P1)

A macropad owner opens the application, sets the physical layout of their pad (number of rows, columns, and knobs), and sees a visual representation of the pad matching that layout. They click any button or knob in the visual layout and assign an action to it (for example, "ctrl-c" or a media key). When done, they save their work as a configuration file that the existing ch57x-keyboard-tool can consume.

**Why this priority**: This is the core value of the entire project — replacing hand-editing of a YAML file with a visual editor. Without layout definition and key assignment, nothing else matters.

**Independent Test**: Can be fully tested by launching the app, configuring a 3×4 pad with 2 knobs, assigning actions to several keys and a knob, saving the file, and confirming the resulting file passes `ch57x-keyboard-tool validate`.

**Acceptance Scenarios**:

1. **Given** a fresh application start, **When** the user sets rows to 3, columns to 4, and knobs to 2, **Then** the visual layout displays a 3×4 grid of buttons and 2 knobs.
2. **Given** a displayed layout, **When** the user selects a button and enters an action (e.g., "ctrl-c"), **Then** the button visibly shows its assigned action in the layout.
3. **Given** a layout with knobs, **When** the user selects a knob, **Then** they can assign three distinct actions: rotate counter-clockwise, press, and rotate clockwise.
4. **Given** a configured layout, **When** the user saves the configuration, **Then** a YAML file is produced that the existing command-line tool accepts as valid.
5. **Given** a configured layout, **When** the user changes the layout dimensions (e.g., from 3×4 to 3×2), **Then** the visual layout updates and the user is warned if existing assignments would be lost.

---

### User Story 2 - Edit an Existing Configuration File (Priority: P2)

A user who already has a working YAML configuration (hand-written or previously created in the GUI) opens it in the application. The GUI displays the layout and all existing key mappings exactly as defined in the file. The user changes a few mappings and saves the file again.

**Why this priority**: Reconfiguration is explicitly requested ("set and reconfigure the key mappings"). Most users will tweak an existing setup far more often than starting from scratch, but this story depends on the editor from Story 1 existing first.

**Independent Test**: Can be tested by opening the repository's `example-mapping.yaml`, verifying every button and knob assignment appears in the GUI as written in the file, changing one assignment, saving, and confirming only that assignment changed.

**Acceptance Scenarios**:

1. **Given** an existing valid configuration file, **When** the user opens it in the GUI, **Then** the layout (rows, columns, knobs, orientation) and all key/knob assignments are displayed as defined in the file.
2. **Given** an opened configuration, **When** the user modifies an assignment and saves, **Then** the saved file reflects the change while preserving all other assignments.
3. **Given** a malformed or unsupported configuration file, **When** the user attempts to open it, **Then** the application shows a clear error message describing the problem instead of crashing or silently loading partial data.

---

### User Story 3 - Manage Multiple Layers (Priority: P2)

A user whose macropad supports layer switching (the common hardware supports three layers) switches between layers in the GUI and assigns a different set of mappings to each layer.

**Why this priority**: The configuration format is built around layers, and the typical supported hardware has three. A GUI that only handles one layer would produce incomplete configurations for most real devices.

**Independent Test**: Can be tested by assigning different actions to the same button position on layer 1 and layer 2, saving, and confirming the saved file contains both layers with the correct distinct assignments.

**Acceptance Scenarios**:

1. **Given** a configured layout, **When** the user switches to another layer, **Then** the visual layout shows that layer's assignments (empty if none have been set).
2. **Given** multiple layers with assignments, **When** the user saves, **Then** all layers are written to the configuration file in order.
3. **Given** a single-layer device, **When** the user keeps only one layer, **Then** the saved file contains exactly one layer and remains valid.

---

### User Story 4 - Guided Action Entry with Validation (Priority: P3)

Instead of memorizing the action syntax (key names, modifier combinations, sequences, mouse actions, media keys), the user picks actions through a guided interface — for example choosing modifiers and a key from lists, or selecting a media action by name — and the application builds the correctly formatted action string. Invalid entries are flagged before saving.

**Why this priority**: This delivers the "easy way to set key mappings" beyond a plain text field. It substantially lowers the learning curve but the editor is still usable without it by typing action strings directly.

**Independent Test**: Can be tested by building "ctrl-shift-a" through the guided picker without typing any syntax, and by entering an invalid action string and confirming the application flags it before save.

**Acceptance Scenarios**:

1. **Given** the action editor for a button, **When** the user selects modifiers and a key from the guided interface, **Then** the correctly formatted action string is generated (e.g., "ctrl-shift-a").
2. **Given** the action editor, **When** the user enters an action that is not valid for the tool (e.g., an unknown key name), **Then** the application indicates the entry is invalid and identifies what is wrong.
3. **Given** the action editor, **When** the user wants a multi-step sequence (e.g., "ctrl-a,ctrl-c"), **Then** they can compose a sequence of up to 5 chords as supported by the hardware.
4. **Given** the action editor, **When** the user wants a media or mouse action, **Then** these are available to pick from named lists (play, mute, volumeup, click, wheelup, etc.).

---

### Edge Cases

- What happens when the user shrinks the layout (fewer rows/columns/knobs) after assigning actions to positions that would no longer exist? The application must warn before discarding those assignments.
- What happens when the user opens a YAML file with valid syntax but values outside supported ranges (e.g., more knobs than any supported device)? The application must report which value is unsupported.
- What happens when a configuration file contains actions the GUI's guided picker doesn't model (e.g., raw HID codes like `<100>`, delay options like `{delay(100)}`)? These must not be corrupted — the GUI preserves them as-is and allows editing them as text.
- What happens when the user tries to save with some keys left unassigned? Unassigned keys must still produce a valid file (a sensible placeholder/no-op or prompting the user), never an invalid one.
- What happens when the user closes the application with unsaved changes? The application must prompt to save or discard.
- Knob count of zero (e.g., the 4×1 no-knob pad) must be supported — the layout simply shows no knobs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to specify the macropad layout: number of rows, number of columns, and number of knobs (including zero knobs).
- **FR-002**: The application MUST display a visual representation of the pad that matches the specified layout, with each button and knob individually selectable.
- **FR-003**: Users MUST be able to assign an action to any button, and three actions (counter-clockwise rotate, press, clockwise rotate) to any knob.
- **FR-004**: Users MUST be able to view, change, and clear any existing assignment (reconfigure without starting over).
- **FR-005**: The application MUST save configurations as YAML files conforming to the format consumed by ch57x-keyboard-tool (model, orientation, rows, columns, knobs, layers with buttons and knobs).
- **FR-006**: The application MUST open existing YAML configuration files and populate the layout and all assignments from them.
- **FR-007**: The application MUST support multiple layers (at least the three layers common to supported hardware), letting the user switch layers and edit each independently.
- **FR-008**: The application MUST support the full action vocabulary of the tool: simple keys, modifier combinations, key sequences (up to 5 chords), mouse actions (click, move, drag, wheel and their aliases), media keys, raw HID codes, and sequence options such as delay — at minimum by preserving and accepting them as text.
- **FR-009**: The application MUST validate action entries and layout values before saving and clearly indicate any invalid entry and the reason.
- **FR-010**: The application MUST allow choosing the keyboard model and orientation values defined by the tool (normal, upsidedown, clockwise, counterclockwise).
- **FR-011**: The application MUST warn the user before discarding data: when shrinking a layout would remove assignments, and when closing with unsaved changes.
- **FR-012**: The application MUST report clear, human-readable errors when opening files that are malformed or contain unsupported values, without crashing.
- **FR-013**: Saved files MUST be usable by the existing command-line workflow without modification (i.e., pass the tool's `validate` command).

### Key Entities

- **Configuration**: The complete description of a macropad setup — keyboard model, orientation, layout dimensions (rows, columns, knobs), and an ordered list of layers. Corresponds one-to-one with a YAML file.
- **Layout**: The physical arrangement — rows × columns of buttons plus a count of knobs. Determines how many assignable positions exist.
- **Layer**: One full set of assignments for every button and knob. A configuration holds one or more layers (commonly three).
- **Button Assignment**: The action bound to one button position within a layer.
- **Knob Assignment**: The trio of actions (ccw, press, cw) bound to one knob within a layer.
- **Action**: What a key press or knob event emulates — a key chord, a sequence of chords, a mouse action, or a media key, expressed in the tool's action syntax.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with no knowledge of the YAML format can create a complete, valid configuration for a 3×4 + 2-knob pad in under 5 minutes.
- **SC-002**: 100% of configurations saved by the GUI pass the existing tool's validation without manual editing.
- **SC-003**: The repository's example configuration file opens in the GUI with every assignment displayed correctly (zero data loss on open → save round-trip).
- **SC-004**: Users can change a single key mapping on an existing configuration and re-save in under 1 minute.
- **SC-005**: Invalid action entries are caught before saving in 100% of cases covered by the tool's documented action syntax, with an error message identifying the offending entry.

## Assumptions

- The GUI's job ends at producing/editing the YAML file; uploading to the device remains the job of the existing command-line tool. (Offering a convenience button to invoke the tool may be considered later but is not required for this feature.)
- Layout limits follow known supported hardware (up to roughly 5 rows/columns and 0–3 knobs); the GUI need not support arbitrary large grids.
- Layers are capped at three, matching all known supported hardware.
- The set of valid key names, modifiers, media keys, and mouse actions is taken from the tool's documentation (`doc/actions.md`) and `show-keys` output; the GUI mirrors that vocabulary rather than defining its own.
- Desktop usage on the platforms where the command-line tool runs (Windows, macOS, Linux) is the target context; Windows is the primary environment for this user.
- Single-user, local-file workflow — no accounts, networking, or shared storage involved.
- Exotic or future action syntax not modeled by a guided picker is handled via raw text entry and preserved verbatim, so the GUI never blocks a power user.
