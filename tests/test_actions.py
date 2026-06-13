"""Grammar tests: every documented example plus known-invalid inputs.

Valid examples come from ch57x-keyboard-tool/doc/actions.md and
example-mapping.yaml.  Note that doc/actions.md mentions ``esc``,
``del`` and ``ctrl-alt-del`` in prose examples, but the tool's parser
(src/keyboard/mod.rs) only knows ``escape`` and ``delete`` -- those
strings are rejected by the real tool and therefore belong in the
invalid list here.
"""

import pytest

from macropad_gui.actions import Action, ActionError, ActionKind, parse_action, serialize_action

KEYBOARD = ActionKind.KEYBOARD_MACRO
MEDIA = ActionKind.MEDIA
MOUSE = ActionKind.MOUSE

VALID = [
    # simple keys (doc/actions.md "Simple Keys")
    ("a", KEYBOARD),
    ("slash", KEYBOARD),
    ("enter", KEYBOARD),
    ("space", KEYBOARD),
    ("f1", KEYBOARD),
    ("escape", KEYBOARD),
    ("<101>", KEYBOARD),
    ("<0>", KEYBOARD),
    ("<255>", KEYBOARD),
    # combinations
    ("ctrl-c", KEYBOARD),
    ("cmd-v", KEYBOARD),
    ("alt-tab", KEYBOARD),
    ("shift-a", KEYBOARD),
    ("ctrl-shift-a", KEYBOARD),
    ("win-ctrl-a", KEYBOARD),
    ("rctrl-ralt-f24", KEYBOARD),
    ("shift-<100>", KEYBOARD),
    # modifier-only accords
    ("alt-shift", KEYBOARD),
    ("win-ctrl", KEYBOARD),
    ("ctrl", KEYBOARD),
    # sequences (up to 5 accords)
    ("h,e,l,l,o", KEYBOARD),
    ("ctrl-a,ctrl-c", KEYBOARD),
    ("win-r,c,m,d,enter", KEYBOARD),
    ("alt-ctrl,ctrl-b", KEYBOARD),
    ("a,b,c,d,e", KEYBOARD),
    # options prefix
    ("{delay(100)}left,a,right", KEYBOARD),
    ("{delay(100)}ctrl-a,ctrl-c", KEYBOARD),
    ("{delay(0)}a", KEYBOARD),
    ("{delay(65535)}a", KEYBOARD),
    ("{}a", KEYBOARD),  # empty options block is legal per parse.rs
    # case-insensitive names
    ("CTRL-A", KEYBOARD),
    ("Play", MEDIA),
    # media tokens (all 10 + alias)
    ("next", MEDIA),
    ("previous", MEDIA),
    ("prev", MEDIA),
    ("stop", MEDIA),
    ("play", MEDIA),
    ("mute", MEDIA),
    ("volumeup", MEDIA),
    ("volumedown", MEDIA),
    ("favorites", MEDIA),
    ("calculator", MEDIA),
    ("screenlock", MEDIA),
    # mouse clicks
    ("click(left)", MOUSE),
    ("click(left+right)", MOUSE),
    ("ctrl-click(left)", MOUSE),
    ("shift-click(right)", MOUSE),
    ("ctrl-click(middle)", MOUSE),
    ("click", MOUSE),
    ("lclick", MOUSE),
    ("rclick", MOUSE),
    ("mclick", MOUSE),
    ("click+rclick", MOUSE),
    ("ctrl-mclick", MOUSE),
    ("ctrl-click", MOUSE),
    # mouse move
    ("move(10,0)", MOUSE),
    ("move(-10,0)", MOUSE),
    ("move(0,10)", MOUSE),
    ("move(5,5)", MOUSE),
    ("ctrl-move(10,5)", MOUSE),
    ("ctrl-move(5,5)", MOUSE),
    ("move(-128,127)", MOUSE),
    # mouse drag
    ("drag(left,10,0)", MOUSE),
    ("drag(right,-5,5)", MOUSE),
    ("drag(left+right,0,10)", MOUSE),
    ("shift-drag(left,10,10)", MOUSE),
    ("alt-drag(right,10,0)", MOUSE),
    ("shift-drag(left+middle,0,0)", MOUSE),
    # mouse wheel
    ("wheel(1)", MOUSE),
    ("wheel(-1)", MOUSE),
    ("wheel(3)", MOUSE),
    ("ctrl-wheel(1)", MOUSE),
    ("alt-wheel(1)", MOUSE),
    ("wheelup", MOUSE),
    ("wheeldown", MOUSE),
    ("ctrl-wheelup", MOUSE),
    ("shift-wheelup", MOUSE),
    ("shift-wheeldown", MOUSE),
    # 'left'/'right' as bare words are arrow keys, not mouse buttons
    ("left", KEYBOARD),
    ("right", KEYBOARD),
    ("ctrl-left", KEYBOARD),
    ("ctrl-enter", KEYBOARD),
    ("ctrl-right", KEYBOARD),
    ("macbrightnessdown", KEYBOARD),
    ("macbrightnessup", KEYBOARD),
]

INVALID = [
    "",
    "bogus",
    "ctrl-bogus",
    "a1",          # parse.rs test case
    "a+",          # parse.rs test case
    "esc",         # doc prose, but not a WellKnownCode
    "del",
    "ctrl-alt-del",
    "ctrl-",
    "ctrl--a",
    "a,,b",
    "a,b,c,d,e,f",        # six accords > MAX_ACCORDS
    "<256>",
    "<999>",
    "<>",
    "shift-play",         # media cannot take modifiers
    "play,next",          # media cannot be sequenced
    "wheelup,a",          # mouse cannot be sequenced
    "wheel(200)",         # out of i8 range
    "wheel(+5)",          # '+' sign not in the grammar
    "move(300,0)",
    "move(1)",
    "move(1,2,3)",
    "drag(left,1)",
    "drag(bogus,1,2)",
    "click()",
    "click(bogus)",
    "ctrl-shift-click",   # mouse takes at most ONE modifier
    "win-click",          # win is not a mouse modifier
    "CLICK",              # mouse keywords are case-sensitive tags
    "{delay}a",           # parse.rs test cases
    "{delay()}a",
    "{delay(abc)}a",
    "{delay(65536)}a",    # > u16
    "{delay(100)}",       # options but no accords
    " a",                 # whitespace is never allowed
    "ctrl - a",
    "a, b",
]


@pytest.mark.parametrize("text,kind", VALID)
def test_valid_actions(text, kind):
    action = parse_action(text)
    assert action.kind is kind
    assert action.text == text
    assert serialize_action(action) == text


@pytest.mark.parametrize("text", INVALID)
def test_invalid_actions(text):
    with pytest.raises(ActionError) as excinfo:
        parse_action(text)
    assert excinfo.value.reason
    assert excinfo.value.position >= 0


def test_error_names_unknown_key():
    with pytest.raises(ActionError) as excinfo:
        parse_action("ctrl-bogus")
    assert "bogus" in excinfo.value.reason


def test_action_is_immutable():
    action = parse_action("ctrl-c")
    with pytest.raises(AttributeError):
        action.text = "x"


def test_every_example_mapping_cell_parses(example_yaml_path):
    """Every action string in the golden example file must parse."""
    import re
    text = example_yaml_path.read_text(encoding="utf-8")
    for value in re.findall(r'"([^"]+)"', text):
        action = parse_action(value)
        assert isinstance(action, Action)
