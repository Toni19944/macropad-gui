"""Action vocabulary and parser for ch57x-keyboard-tool action strings.

This is a Python mirror of the grammar implemented in
``ch57x-keyboard-tool/src/parse.rs`` and the enums in
``ch57x-keyboard-tool/src/keyboard/mod.rs`` (research R4).  Behavioural
notes carried over from the Rust parser:

- The top-level parser tries mouse, then media, then keyboard, and the
  whole input must be consumed.  If an earlier branch matches a *prefix*
  of the input, the parse fails rather than falling through (this is how
  nom's ``alt`` + ``all_consuming`` behave), so e.g. ``play,next`` is
  invalid even though ``play`` alone is valid.
- Keyword tags such as ``click(`` / ``wheelup`` / ``move(`` / ``delay(``
  are case-sensitive (nom ``tag``); names looked up in enums (modifiers,
  keys, media tokens, mouse buttons) are ASCII case-insensitive (strum
  ``ascii_case_insensitive``).
- Mouse events accept at most ONE modifier prefix, limited to
  ctrl/shift/alt.
- No whitespace is allowed anywhere.

Unassigned positions are serialized as ``<0>`` (HID code 0 = no-op,
research R6); the GUI displays them as "(unassigned)".
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Vocabulary (ground truth: src/keyboard/mod.rs)
# --------------------------------------------------------------------------

#: Canonical serialized form of an unassigned position (research R6).
UNASSIGNED = "<0>"

#: Keyboard modifiers in display order (canonical names).
MODIFIERS = (
    "ctrl", "shift", "alt", "win",
    "rctrl", "rshift", "ralt", "rwin",
)

#: Accepted modifier aliases -> canonical name.
MODIFIER_ALIASES = {"opt": "alt", "cmd": "win", "ropt": "ralt", "rcmd": "rwin"}

_MODIFIER_NAMES = frozenset(MODIFIERS) | frozenset(MODIFIER_ALIASES)

#: WellKnownCode names in enum order (for the guided picker's key list).
WELL_KNOWN_KEYS = tuple("abcdefghijklmnopqrstuvwxyz") + tuple("1234567890") + (
    "enter", "escape", "backspace", "tab", "space",
    "minus", "equal", "leftbracket", "rightbracket", "backslash",
    "nonushash", "semicolon", "quote", "grave", "comma", "dot", "slash",
    "capslock",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "printscreen", "scrolllock", "pause",
    "insert", "home", "pageup", "delete", "end", "pagedown",
    "right", "left", "down", "up",
    "numlock", "numpadslash", "numpadasterisk", "numpadminus", "numpadplus",
    "numpadenter",
    "numpad1", "numpad2", "numpad3", "numpad4", "numpad5",
    "numpad6", "numpad7", "numpad8", "numpad9", "numpad0",
    "numpaddot", "nonusbackslash", "application", "power", "numpadequal",
    "f13", "f14", "f15", "f16", "f17", "f18", "f19", "f20",
    "f21", "f22", "f23", "f24",
)

#: Accepted key-name aliases -> canonical name.
KEY_ALIASES = {"macbrightnessdown": "scrolllock", "macbrightnessup": "pause"}

_KEY_NAMES = frozenset(WELL_KNOWN_KEYS) | frozenset(KEY_ALIASES)

#: Media tokens in display order (canonical names).
MEDIA_CODES = (
    "next", "previous", "stop", "play", "mute",
    "volumeup", "volumedown", "favorites", "calculator", "screenlock",
)

#: Accepted media aliases -> canonical name.
MEDIA_ALIASES = {"prev": "previous"}

_MEDIA_NAMES = frozenset(MEDIA_CODES) | frozenset(MEDIA_ALIASES)

#: Modifiers allowed on mouse events (no win/cmd).
MOUSE_MODIFIERS = ("ctrl", "shift", "alt")
_MOUSE_MODIFIER_NAMES = frozenset(MOUSE_MODIFIERS)

MOUSE_BUTTONS = ("left", "right", "middle")
_MOUSE_BUTTON_NAMES = frozenset(MOUSE_BUTTONS)

#: Maximum accords in a keyboard macro sequence (doc/actions.md; the
#: ch57x-2 firmware limit -- the safe common bound across models).
MAX_ACCORDS = 5

#: Maximum {delay(ms)} value (u16 in the tool).
MAX_DELAY = 65535


class ActionKind(enum.Enum):
    KEYBOARD_MACRO = "keyboard"
    MEDIA = "media"
    MOUSE = "mouse"


class ActionError(ValueError):
    """An action string failed to parse.

    ``position`` is the 0-based character offset of the problem and
    ``reason`` a human-readable explanation (FR-009 / SC-005).
    """

    def __init__(self, position: int, reason: str):
        self.position = position
        self.reason = reason
        super().__init__(f"{reason} (at position {position})")


@dataclass(frozen=True)
class Action:
    """Validated action string; ``text`` is written to YAML verbatim."""

    text: str
    kind: ActionKind


def serialize_action(action: Action) -> str:
    return action.text


# --------------------------------------------------------------------------
# Parser internals
# --------------------------------------------------------------------------


class _NoMatch(Exception):
    """Backtrackable parse failure (nom's recoverable Error)."""


def _alpha(text: str, pos: int) -> tuple[str, int]:
    end = pos
    while end < len(text) and text[end].isascii() and text[end].isalpha():
        end += 1
    if end == pos:
        raise _NoMatch
    return text[pos:end], end


def _alnum(text: str, pos: int) -> tuple[str, int]:
    end = pos
    while end < len(text) and text[end].isascii() and text[end].isalnum():
        end += 1
    if end == pos:
        raise _NoMatch
    return text[pos:end], end


def _digits(text: str, pos: int) -> tuple[str, int]:
    end = pos
    while end < len(text) and text[end].isdigit():
        end += 1
    if end == pos:
        raise _NoMatch
    return text[pos:end], end


def _tag(text: str, pos: int, tag: str) -> int:
    if text.startswith(tag, pos):
        return pos + len(tag)
    raise _NoMatch


def _delta(text: str, pos: int) -> tuple[int, int]:
    """Signed i8 (-128..127): optional '-' then digits."""
    p = pos
    negative = False
    if p < len(text) and text[p] == "-":
        negative = True
        p += 1
    digits, p = _digits(text, p)
    value = -int(digits) if negative else int(digits)
    if not -128 <= value <= 127:
        raise _NoMatch
    return value, p


# ---- mouse ----------------------------------------------------------------


def _mouse_buttons(text: str, pos: int) -> int:
    word, p = _alpha(text, pos)
    if word.lower() not in _MOUSE_BUTTON_NAMES:
        raise _NoMatch
    # '+'-separated list; a trailing '+' without a valid button backtracks
    # (mirrors nom separated_list1).
    while p < len(text) and text[p] == "+":
        try:
            word, p2 = _alpha(text, p + 1)
        except _NoMatch:
            break
        if word.lower() not in _MOUSE_BUTTON_NAMES:
            break
        p = p2
    return p


def _click_alias(text: str, pos: int) -> int:
    for tag in ("click", "lclick", "rclick", "mclick"):
        try:
            return _tag(text, pos, tag)
        except _NoMatch:
            continue
    raise _NoMatch


def _mouse_action(text: str, pos: int) -> int:
    # click(buttons)
    try:
        p = _tag(text, pos, "click(")
        p = _mouse_buttons(text, p)
        return _tag(text, p, ")")
    except _NoMatch:
        pass
    # click aliases, '+'-combinable: click+rclick
    try:
        p = _click_alias(text, pos)
        while p < len(text) and text[p] == "+":
            try:
                p2 = _click_alias(text, p + 1)
            except _NoMatch:
                break
            p = p2
        return p
    except _NoMatch:
        pass
    # wheel(n) | wheelup | wheeldown
    try:
        p = _tag(text, pos, "wheel(")
        _, p = _delta(text, p)
        return _tag(text, p, ")")
    except _NoMatch:
        pass
    for tag in ("wheelup", "wheeldown"):
        try:
            return _tag(text, pos, tag)
        except _NoMatch:
            continue
    # move(x,y) -- committed once "move(" matched (nom `cut`)
    try:
        p = _tag(text, pos, "move(")
    except _NoMatch:
        p = None
    if p is not None:
        try:
            _, p = _delta(text, p)
            p = _tag(text, p, ",")
            _, p = _delta(text, p)
            return _tag(text, p, ")")
        except _NoMatch:
            raise ActionError(
                p, "move must be move(x,y) with x and y in -128..127")
    # drag(buttons,x,y) -- committed once "drag(" matched
    try:
        p = _tag(text, pos, "drag(")
    except _NoMatch:
        p = None
    if p is not None:
        try:
            p = _mouse_buttons(text, p)
            p = _tag(text, p, ",")
            _, p = _delta(text, p)
            p = _tag(text, p, ",")
            _, p = _delta(text, p)
            return _tag(text, p, ")")
        except _NoMatch:
            raise ActionError(
                p, "drag must be drag(buttons,x,y) with buttons from "
                   "left/right/middle and x,y in -128..127")
    raise _NoMatch


def _mouse_event(text: str, pos: int) -> int:
    p = pos
    # Single optional modifier prefix (parse.rs allows at most one,
    # despite the contract's EBNF suggesting repetition).
    try:
        word, p2 = _alpha(text, pos)
        if word.lower() in _MOUSE_MODIFIER_NAMES and p2 < len(text) \
                and text[p2] == "-":
            p = p2 + 1
    except _NoMatch:
        pass
    # Once a modifier prefix is consumed, the action must follow -- no
    # retry without the prefix (mirrors nom tuple semantics).
    return _mouse_action(text, p)


# ---- media ----------------------------------------------------------------


def _media(text: str, pos: int) -> int:
    word, p = _alpha(text, pos)
    if word.lower() in _MEDIA_NAMES:
        return p
    raise _NoMatch


# ---- keyboard -------------------------------------------------------------


def _try_code(text: str, pos: int) -> int | None:
    """Key code: ``<N>`` (0..255) or a well-known key name."""
    if pos < len(text) and text[pos] == "<":
        try:
            digits, p = _digits(text, pos + 1)
            p = _tag(text, p, ">")
        except _NoMatch:
            raise ActionError(
                pos, "raw HID code must look like <N> with N in 0..255")
        value = int(digits)
        if value > 255:
            raise ActionError(pos, f"HID code {value} out of range 0..255")
        return p
    try:
        word, p = _alnum(text, pos)
    except _NoMatch:
        return None
    if word.lower() in _KEY_NAMES:
        return p
    return None


def _try_modifier(text: str, pos: int) -> int | None:
    try:
        word, p = _alpha(text, pos)
    except _NoMatch:
        return None
    if word.lower() in _MODIFIER_NAMES:
        return p
    return None


def _accord(text: str, pos: int) -> int:
    # Branch 1: bare key code (covers "a", "<100>", "f1", ...).
    p = _try_code(text, pos)
    if p is not None:
        return p
    # Branch 2: (modifier '-')* then key code or final bare modifier.
    p = pos
    while True:
        m = _try_modifier(text, p)
        if m is None or m >= len(text) or text[m] != "-":
            break
        p = m + 1
    r = _try_code(text, p)
    if r is not None:
        return r
    r = _try_modifier(text, p)
    if r is not None:
        return r
    try:
        word, _ = _alnum(text, p)
    except _NoMatch:
        word = text[p:p + 1] or "<end of input>"
    raise ActionError(p, f"unknown key or modifier {word!r}")


def _try_option(text: str, pos: int) -> int | None:
    try:
        p = _tag(text, pos, "delay(")
    except _NoMatch:
        return None
    try:
        digits, p = _digits(text, p)
        p = _tag(text, p, ")")
    except _NoMatch:
        raise ActionError(pos, "option must be delay(<milliseconds>)")
    value = int(digits)
    if value > MAX_DELAY:
        raise ActionError(pos, f"delay {value} out of range 0..{MAX_DELAY}")
    return p


def _macro_options(text: str, pos: int) -> int:
    # pos points at '{'; zero options ("{}") is legal per parse.rs.
    p = pos + 1
    r = _try_option(text, p)
    if r is not None:
        p = r
        while p < len(text) and text[p] == ",":
            r = _try_option(text, p + 1)
            if r is None:
                break
            p = r
    try:
        return _tag(text, p, "}")
    except _NoMatch:
        raise ActionError(
            p, "invalid options block: expected delay(<ms>) entries "
               "wrapped in {...}")


def _keyboard(text: str, pos: int) -> int:
    p = pos
    if p < len(text) and text[p] == "{":
        p = _macro_options(text, p)
    p = _accord(text, p)
    count = 1
    while p < len(text) and text[p] == ",":
        p = _accord(text, p + 1)
        count += 1
    if count > MAX_ACCORDS:
        raise ActionError(
            pos, f"too many accords: {count} (maximum {MAX_ACCORDS})")
    return p


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------


def parse_action(text: str) -> Action:
    """Parse and validate an action string.

    Returns an :class:`Action` with the derived kind, or raises
    :class:`ActionError` with the offending position and reason.
    """
    if not text:
        raise ActionError(0, "action is empty")

    try:
        p = _mouse_event(text, 0)
    except _NoMatch:
        p = None
    if p is not None:
        if p != len(text):
            raise ActionError(
                p, f"unexpected text {text[p:]!r} after mouse action")
        return Action(text, ActionKind.MOUSE)

    try:
        p = _media(text, 0)
    except _NoMatch:
        p = None
    if p is not None:
        if p != len(text):
            raise ActionError(
                p, f"unexpected text {text[p:]!r} after media action "
                   "(media actions cannot be combined)")
        return Action(text, ActionKind.MEDIA)

    p = _keyboard(text, 0)
    if p != len(text):
        raise ActionError(p, f"unexpected text {text[p:]!r}")
    return Action(text, ActionKind.KEYBOARD_MACRO)
