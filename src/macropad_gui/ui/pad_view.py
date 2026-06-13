"""Visual pad: grid of buttons plus knob widgets for one layer.

Positions passed to ``on_select`` are tuples:
``("button", row, col)`` or ``("knob", index, part)`` with part one of
ccw/press/cw.  The grid is drawn in file order (``Config.grid_shape``),
so vertical orientations show the transposed grid exactly as the YAML
lays it out.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from ..actions import Action
from ..model import Config

_LABEL_WIDTH = 14
_KNOB_GLYPHS = (("ccw", "↺ ccw"), ("press", "⏎ press"), ("cw", "↻ cw"))

Position = tuple


def _label(action: Action | None) -> str:
    if action is None:
        return "(unassigned)"
    text = action.text
    if len(text) > _LABEL_WIDTH:
        return text[:_LABEL_WIDTH - 1] + "…"
    return text


class PadView(ttk.Frame):
    def __init__(self, master, config: Config,
                 on_select: Callable[[Position], None],
                 layer_index: int = 0):
        super().__init__(master, padding=8)
        self.on_select = on_select
        self._config = config
        self._layer_index = layer_index
        self.refresh()

    def refresh(self, config: Config | None = None,
                layer_index: int | None = None) -> None:
        """Destroy and redraw all widgets to match the (new) config."""
        if config is not None:
            self._config = config
        if layer_index is not None:
            self._layer_index = layer_index
        if self._layer_index >= len(self._config.layers):
            self._layer_index = 0
        for child in self.winfo_children():
            child.destroy()

        layer = self._config.layers[self._layer_index]

        grid = ttk.LabelFrame(self, text="Buttons", padding=6)
        for r, row in enumerate(layer.buttons):
            for c, action in enumerate(row):
                button = ttk.Button(
                    grid, text=_label(action), width=_LABEL_WIDTH,
                    command=lambda r=r, c=c: self.on_select(("button", r, c)))
                button.grid(row=r, column=c, padx=3, pady=3)
        grid.pack(side="left", anchor="n")

        if layer.knobs:
            knobs = ttk.Frame(self)
            for k, knob in enumerate(layer.knobs):
                frame = ttk.LabelFrame(knobs, text=f"Knob {k + 1}", padding=4)
                for part, glyph in _KNOB_GLYPHS:
                    ttk.Button(
                        frame, text=f"{glyph}: {_label(knob.get(part))}",
                        width=_LABEL_WIDTH + 8,
                        command=lambda k=k, part=part:
                            self.on_select(("knob", k, part)),
                    ).pack(fill="x", pady=1)
                frame.pack(fill="x", pady=(0, 6))
            knobs.pack(side="left", anchor="n", padx=(12, 0))

    @property
    def layer_index(self) -> int:
        return self._layer_index
