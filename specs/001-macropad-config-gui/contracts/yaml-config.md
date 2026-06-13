# Contract: ch57x-keyboard-tool YAML Configuration File

**Feature**: 001-macropad-config-gui | **Date**: 2026-06-13

This is the external contract between the GUI and the existing CLI tool. The GUI is the *producer*; `ch57x-keyboard-tool validate|upload` is the *consumer*. Ground truth: `ch57x-keyboard-tool/src/config.rs`, `src/parse.rs`, `src/keyboard/mod.rs` (pinned to the clone in this repo). **Acceptance test: every file the GUI saves must pass `ch57x-keyboard-tool validate <file>`.**

## File schema

```yaml
model: ch57x-2            # optional; ch57x-1 | ch57x-2 | ch57x-3
orientation: normal       # normal | upsidedown | clockwise | counterclockwise
rows: 3                   # buttons grid, counted in normal orientation
columns: 4
knobs: 2                  # 0 = no knobs
layers:                   # 1..3 entries
  - buttons:              # horizontal orientations: `rows` lists × `columns` items
                          # vertical orientations: `columns` lists × `rows` items
      - ["a", "ctrl-a", "alt-shift", "alt-ctrl,ctrl-b"]
      - ["e", "f", "g", "h"]
      - ["<100>", "j", "k", "l"]
    knobs:                # exactly `knobs` entries; left→right (horizontal) / top→bottom (vertical)
      - ccw: "wheelup"
        press: "click"
        cw: "wheeldown"
```

Notes the GUI must honor:
- In `clockwise`/`counterclockwise` orientation the `buttons` grid is transposed (`columns` rows of `rows` items) — see `reorient_grid` in config.rs.
- Unknown extra fields and YAML comments in hand-written files must be preserved on save (GUI-side guarantee, SC-003).
- Every grid cell and knob field must contain a parseable action string; the GUI writes `<0>` for unassigned positions.

## Action string grammar (EBNF, mirrors parse.rs)

```ebnf
action        = keyboard_macro | media | mouse_event ;

keyboard_macro = [ options ] accord { "," accord } ;     (* 1..5 accords *)
options       = "{" option { "," option } "}" ;
option        = "delay(" number ")" ;
accord        = { modifier "-" } key
              | modifier { "-" modifier } ;              (* modifier-only accord is legal *)
key           = well_known_key | "<" u8 ">" ;            (* u8: 0..255 decimal *)
modifier      = "ctrl" | "shift" | "alt" | "opt" | "win" | "cmd"
              | "rctrl" | "rshift" | "ralt" | "ropt" | "rwin" | "rcmd" ;

media         = "next" | "previous" | "prev" | "stop" | "play" | "mute"
              | "volumeup" | "volumedown" | "favorites" | "calculator" | "screenlock" ;

mouse_event   = [ mouse_mod_prefix ] mouse_action ;
mouse_mod_prefix = ( "ctrl" | "shift" | "alt" ) "-" { ( "ctrl" | "shift" | "alt" ) "-" } ;
mouse_action  = click | wheel | move | drag ;
click         = "click(" buttons ")" | "click" | "lclick" | "rclick" | "mclick" ;
buttons       = button { "+" button } ;
button        = "left" | "right" | "middle" ;
wheel         = "wheel(" i8 ")" | "wheelup" | "wheeldown" ;
move          = "move(" i8 "," i8 ")" ;
drag          = "drag(" buttons "," i8 "," i8 ")" ;     (* i8: -128..127 *)
```

All tokens are ASCII case-insensitive.

## Well-known key names

`a`–`z` · `0`–`9` · `enter` `escape` `backspace` `tab` `space` · `minus` `equal` `leftbracket` `rightbracket` `backslash` `nonushash` `semicolon` `quote` `grave` `comma` `dot` `slash` · `capslock` · `f1`–`f24` · `printscreen` · `scrolllock`/`macbrightnessdown` · `pause`/`macbrightnessup` · `insert` `home` `pageup` `delete` `end` `pagedown` · `right` `left` `down` `up` · `numlock` `numpadslash` `numpadasterisk` `numpadminus` `numpadplus` `numpadenter` `numpad0`–`numpad9` `numpaddot` `numpadequal` · `nonusbackslash` `application` `power`

## Semantic rules beyond the grammar

| Rule | Source |
|---|---|
| Media tokens cannot be combined with modifiers or other keys | doc/actions.md |
| Keyboard macros: max 5 accords | doc/actions.md |
| Mouse modifiers limited to ctrl/shift/alt (no win/cmd) | parse.rs `mouse_modifier` |
| move/drag/wheel numeric range −128…127 | doc/actions.md, i8 in parse.rs |
| Letters mean physical QWERTY keys, not produced characters | doc/actions.md (GUI shows a hint, no validation impact) |
| 3x1-pad limitation (modifiers only on first accord) | README; GUI shows a warning when model/layout suggests 3×1, does not block |

## Versioning

The contract is pinned to the cloned tool at `ch57x-keyboard-tool/` (no submodule/version pinning beyond the checked-in copy). If the clone is updated, `tests/test_actions.py` and the golden round-trip test against `example-mapping.yaml` are the regression tripwire.
