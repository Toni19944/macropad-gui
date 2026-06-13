"""Action editor dialog: guided picker tabs + raw text with live validation.

The guided tabs (Keyboard / Media / Mouse) only ever *generate* text into
the raw entry at the bottom; the raw entry is the single source of truth
and is validated on every change with ``actions.parse_action`` (FR-009).
Anything the picker cannot compose (exotic combinations, raw HID codes)
stays editable as raw text and is preserved verbatim (FR-008).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..actions import (
    MAX_ACCORDS,
    MAX_DELAY,
    MEDIA_CODES,
    MODIFIERS,
    MOUSE_BUTTONS,
    MOUSE_MODIFIERS,
    WELL_KNOWN_KEYS,
    ActionError,
    parse_action,
)

_LIMITED_PAD_NOTE = (
    "Note: this 1-row/1-column + 1-knob pad only supports modifiers on "
    "the FIRST chord of a sequence (e.g. ctrl-a,b but not a,ctrl-b)."
)


class ActionEditor(tk.Toplevel):
    """Modal dialog; after wait_window(), ``result`` is None when
    cancelled, ``""`` to clear the assignment, or a valid action string."""

    def __init__(self, master, position_label: str, initial_text: str = "",
                 limited_pad: bool = False):
        super().__init__(master)
        self.title(f"Assign action — {position_label}")
        self.resizable(False, False)
        self.result: str | None = None

        self._notebook = ttk.Notebook(self)
        self._build_keyboard_tab()
        self._build_media_tab()
        self._build_mouse_tab()
        self._notebook.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        if limited_pad:
            ttk.Label(self, text=_LIMITED_PAD_NOTE, wraplength=420,
                      foreground="#a06000").pack(fill="x", padx=8, pady=(0, 4))

        raw = ttk.Frame(self)
        ttk.Label(raw, text="Action text:").pack(side="left")
        self._text_var = tk.StringVar(value=initial_text)
        self._entry = ttk.Entry(raw, textvariable=self._text_var, width=46)
        self._entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self._entry.bind("<KeyRelease>", lambda _e: self._validate())
        raw.pack(fill="x", padx=8, pady=4)

        self._status = ttk.Label(self, text="", wraplength=440)
        self._status.pack(fill="x", padx=8, pady=(0, 4))

        buttons = ttk.Frame(self)
        self._ok = ttk.Button(buttons, text="OK", command=self._on_ok)
        self._ok.pack(side="right", padx=(4, 0))
        ttk.Button(buttons, text="Cancel", command=self._on_cancel).pack(side="right")
        buttons.pack(fill="x", padx=8, pady=(0, 8))

        self.bind("<Return>", lambda _e: self._on_ok())
        self.bind("<Escape>", lambda _e: self._on_cancel())
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._validate()
        self._entry.focus_set()
        self.transient(master)
        self.grab_set()

    # -- keyboard tab --------------------------------------------------

    def _build_keyboard_tab(self) -> None:
        tab = ttk.Frame(self._notebook, padding=8)
        self._notebook.add(tab, text="Keyboard")

        mods = ttk.LabelFrame(tab, text="Modifiers", padding=4)
        self._mod_vars: dict[str, tk.BooleanVar] = {}
        for i, name in enumerate(MODIFIERS):
            var = tk.BooleanVar(value=False)
            self._mod_vars[name] = var
            ttk.Checkbutton(mods, text=name, variable=var,
                            command=self._compose_keyboard).grid(
                row=i // 4, column=i % 4, sticky="w", padx=2)
        mods.pack(fill="x")

        keyrow = ttk.Frame(tab)
        ttk.Label(keyrow, text="Key:").pack(side="left")
        self._key_var = tk.StringVar(value="")
        key_box = ttk.Combobox(keyrow, textvariable=self._key_var,
                               values=("",) + WELL_KNOWN_KEYS, width=18)
        key_box.pack(side="left", padx=(4, 12))
        key_box.bind("<<ComboboxSelected>>", lambda _e: self._compose_keyboard())
        key_box.bind("<KeyRelease>", lambda _e: self._compose_keyboard())
        ttk.Label(keyrow, text="or raw HID <N>:").pack(side="left")
        self._hid_var = tk.StringVar(value="")
        hid = ttk.Entry(keyrow, textvariable=self._hid_var, width=5)
        hid.pack(side="left", padx=4)
        hid.bind("<KeyRelease>", lambda _e: self._compose_keyboard())
        keyrow.pack(fill="x", pady=4)

        seq = ttk.LabelFrame(tab, text=f"Sequence (max {MAX_ACCORDS} chords)",
                             padding=4)
        self._chords: list[str] = []
        self._chord_list = tk.Listbox(seq, height=3, width=40)
        self._chord_list.grid(row=0, column=0, rowspan=2, sticky="nsew")
        ttk.Button(seq, text="Add chord", command=self._add_chord).grid(
            row=0, column=1, sticky="ew", padx=(4, 0))
        ttk.Button(seq, text="Remove last", command=self._remove_chord).grid(
            row=1, column=1, sticky="ew", padx=(4, 0))
        delay_row = ttk.Frame(seq)
        ttk.Label(delay_row, text="delay between chords (ms, 0 = none):").pack(side="left")
        self._delay_var = tk.IntVar(value=0)
        ttk.Spinbox(delay_row, from_=0, to=MAX_DELAY, increment=10,
                    textvariable=self._delay_var, width=7,
                    command=self._compose_keyboard).pack(side="left", padx=4)
        delay_row.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        seq.pack(fill="x", pady=4)

    def _current_chord(self) -> str:
        parts = [name for name in MODIFIERS if self._mod_vars[name].get()]
        hid = self._hid_var.get().strip()
        key = self._key_var.get().strip()
        if hid:
            parts.append(f"<{hid}>")
        elif key:
            parts.append(key)
        return "-".join(parts)

    def _add_chord(self) -> None:
        chord = self._current_chord()
        if not chord or len(self._chords) >= MAX_ACCORDS:
            return
        self._chords.append(chord)
        self._chord_list.insert("end", chord)
        for var in self._mod_vars.values():
            var.set(False)
        self._key_var.set("")
        self._hid_var.set("")
        self._compose_keyboard()

    def _remove_chord(self) -> None:
        if self._chords:
            self._chords.pop()
            self._chord_list.delete("end")
        self._compose_keyboard()

    def _compose_keyboard(self) -> None:
        chords = list(self._chords)
        current = self._current_chord()
        if current:
            chords.append(current)
        text = ",".join(chords)
        try:
            delay = self._delay_var.get()
        except tk.TclError:
            delay = 0
        if text and delay > 0:
            text = f"{{delay({delay})}}{text}"
        self._set_text(text)

    # -- media tab -----------------------------------------------------

    def _build_media_tab(self) -> None:
        tab = ttk.Frame(self._notebook, padding=8)
        self._notebook.add(tab, text="Media")
        ttk.Label(tab, text="Media action (cannot be combined with keys "
                            "or modifiers):").pack(anchor="w")
        self._media_list = tk.Listbox(tab, height=len(MEDIA_CODES),
                                      exportselection=False)
        for token in MEDIA_CODES:
            self._media_list.insert("end", token)
        self._media_list.bind("<<ListboxSelect>>", self._on_media_select)
        self._media_list.pack(fill="both", expand=True, pady=4)

    def _on_media_select(self, _event) -> None:
        selection = self._media_list.curselection()
        if selection:
            self._set_text(MEDIA_CODES[selection[0]])

    # -- mouse tab -------------------------------------------------------

    def _build_mouse_tab(self) -> None:
        tab = ttk.Frame(self._notebook, padding=8)
        self._notebook.add(tab, text="Mouse")

        row1 = ttk.Frame(tab)
        ttk.Label(row1, text="Action:").pack(side="left")
        self._mouse_type = tk.StringVar(value="click")
        type_box = ttk.Combobox(row1, textvariable=self._mouse_type,
                                values=("click", "wheel", "move", "drag"),
                                state="readonly", width=8)
        type_box.pack(side="left", padx=4)
        type_box.bind("<<ComboboxSelected>>", lambda _e: self._compose_mouse())
        ttk.Label(row1, text="Modifier:").pack(side="left", padx=(12, 0))
        self._mouse_mod = tk.StringVar(value="")
        mod_box = ttk.Combobox(row1, textvariable=self._mouse_mod,
                               values=("",) + MOUSE_MODIFIERS,
                               state="readonly", width=6)
        mod_box.pack(side="left", padx=4)
        mod_box.bind("<<ComboboxSelected>>", lambda _e: self._compose_mouse())
        row1.pack(fill="x", pady=2)

        row2 = ttk.Frame(tab)
        ttk.Label(row2, text="Buttons (click/drag):").pack(side="left")
        self._mouse_buttons: dict[str, tk.BooleanVar] = {}
        for name in MOUSE_BUTTONS:
            var = tk.BooleanVar(value=name == "left")
            self._mouse_buttons[name] = var
            ttk.Checkbutton(row2, text=name, variable=var,
                            command=self._compose_mouse).pack(side="left", padx=2)
        row2.pack(fill="x", pady=2)

        row3 = ttk.Frame(tab)
        self._mouse_x = tk.IntVar(value=0)
        self._mouse_y = tk.IntVar(value=0)
        self._mouse_n = tk.IntVar(value=1)
        for label, var in (("x:", self._mouse_x), ("y:", self._mouse_y),
                           ("wheel amount:", self._mouse_n)):
            ttk.Label(row3, text=label).pack(side="left", padx=(8, 0))
            ttk.Spinbox(row3, from_=-128, to=127, textvariable=var, width=5,
                        command=self._compose_mouse).pack(side="left")
        row3.pack(fill="x", pady=2)
        ttk.Label(tab, foreground="#666666",
                  text="Ranges are -128..127. Aliases like wheelup/rclick "
                       "can be typed directly in the action text.").pack(
            anchor="w", pady=(6, 0))

    def _compose_mouse(self) -> None:
        kind = self._mouse_type.get()
        buttons = "+".join(
            name for name in MOUSE_BUTTONS if self._mouse_buttons[name].get())

        def num(var: tk.IntVar) -> int:
            try:
                return var.get()
            except tk.TclError:
                return 0

        if kind == "click":
            text = f"click({buttons})"
        elif kind == "wheel":
            text = f"wheel({num(self._mouse_n)})"
        elif kind == "move":
            text = f"move({num(self._mouse_x)},{num(self._mouse_y)})"
        else:
            text = f"drag({buttons},{num(self._mouse_x)},{num(self._mouse_y)})"
        modifier = self._mouse_mod.get()
        if modifier:
            text = f"{modifier}-{text}"
        self._set_text(text)

    # -- validation / lifecycle ------------------------------------------

    def _set_text(self, text: str) -> None:
        self._text_var.set(text)
        self._validate()

    def _validate(self) -> bool:
        text = self._text_var.get()
        if text == "":
            self._status.configure(
                text="empty — OK leaves this position unassigned",
                foreground="#006000")
            self._ok.state(["!disabled"])
            return True
        try:
            action = parse_action(text)
        except ActionError as e:
            self._status.configure(text=f"invalid: {e.reason}",
                                   foreground="#b00000")
            self._ok.state(["disabled"])
            return False
        self._status.configure(text=f"valid {action.kind.value} action",
                               foreground="#006000")
        self._ok.state(["!disabled"])
        return True

    def _on_ok(self) -> None:
        if not self._validate():
            return
        self.result = self._text_var.get()
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()
