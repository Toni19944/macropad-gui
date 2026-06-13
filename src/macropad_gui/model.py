"""Headless data model: Config, Layout, Layer, KnobBinding.

See specs/001-macropad-config-gui/data-model.md.  Tkinter is never
imported here.  Grids are stored exactly as the YAML file lays them out:
``rows x columns`` for horizontal orientations (normal/upsidedown) and
``columns x rows`` for vertical ones (clockwise/counterclockwise) -- see
``Config.grid_shape()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .actions import Action

ORIENTATIONS = ("normal", "upsidedown", "clockwise", "counterclockwise")
HORIZONTAL_ORIENTATIONS = ("normal", "upsidedown")
KEYBOARD_MODELS = ("ch57x-1", "ch57x-2", "ch57x-3")

MIN_ROWS, MAX_ROWS = 1, 8
MIN_COLUMNS, MAX_COLUMNS = 1, 8
MIN_KNOBS, MAX_KNOBS = 0, 4
MIN_LAYERS, MAX_LAYERS = 1, 3

KNOB_PARTS = ("ccw", "press", "cw")

#: A lost-assignment descriptor returned by Config.resize() and
#: Config.set_layer_count():
#:   ("button", layer_index, row, col)  or  ("knob", layer_index, knob_index, part)
LostAssignment = tuple


@dataclass(frozen=True)
class Layout:
    rows: int
    columns: int
    knobs: int

    def __post_init__(self) -> None:
        if not MIN_ROWS <= self.rows <= MAX_ROWS:
            raise ValueError(f"rows must be {MIN_ROWS}..{MAX_ROWS}, got {self.rows}")
        if not MIN_COLUMNS <= self.columns <= MAX_COLUMNS:
            raise ValueError(
                f"columns must be {MIN_COLUMNS}..{MAX_COLUMNS}, got {self.columns}")
        if not MIN_KNOBS <= self.knobs <= MAX_KNOBS:
            raise ValueError(f"knobs must be {MIN_KNOBS}..{MAX_KNOBS}, got {self.knobs}")


@dataclass
class KnobBinding:
    ccw: Action | None = None
    press: Action | None = None
    cw: Action | None = None

    def get(self, part: str) -> Action | None:
        if part not in KNOB_PARTS:
            raise ValueError(f"unknown knob part {part!r}")
        return getattr(self, part)

    def set(self, part: str, action: Action | None) -> None:
        if part not in KNOB_PARTS:
            raise ValueError(f"unknown knob part {part!r}")
        setattr(self, part, action)


@dataclass
class Layer:
    buttons: list[list[Action | None]]
    knobs: list[KnobBinding]

    @staticmethod
    def empty(grid_rows: int, grid_cols: int, knobs: int) -> "Layer":
        return Layer(
            buttons=[[None] * grid_cols for _ in range(grid_rows)],
            knobs=[KnobBinding() for _ in range(knobs)],
        )


def grid_shape(layout: Layout, orientation: str) -> tuple[int, int]:
    """(rows, cols) of the buttons grid as laid out in the YAML file."""
    if orientation in HORIZONTAL_ORIENTATIONS:
        return layout.rows, layout.columns
    return layout.columns, layout.rows


@dataclass
class Config:
    layout: Layout
    layers: list[Layer]
    model: str | None = None
    orientation: str = "normal"
    source_path: Path | None = None
    dirty: bool = False
    #: Positions whose raw-text entry failed validation (T029); save is
    #: blocked while non-empty.  Keys match LostAssignment tuples.
    errors: dict = field(default_factory=dict)
    #: Cached ruamel.yaml round-trip document (set by yaml_io.load).
    yaml_doc: Any = field(default=None, repr=False, compare=False)
    #: Newline style of the source file, preserved on save.
    newline: str = "\n"

    @classmethod
    def new(cls, rows: int = 3, columns: int = 4, knobs: int = 2,
            layer_count: int = 3, model: str | None = None,
            orientation: str = "normal") -> "Config":
        layout = Layout(rows, columns, knobs)
        gr, gc = grid_shape(layout, orientation)
        return cls(
            layout=layout,
            layers=[Layer.empty(gr, gc, knobs) for _ in range(layer_count)],
            model=model,
            orientation=orientation,
        )

    def grid_shape(self) -> tuple[int, int]:
        return grid_shape(self.layout, self.orientation)

    # -- resizing ----------------------------------------------------------

    def resize(self, new_layout: Layout, *, dry_run: bool = False) -> set[LostAssignment]:
        """Resize to ``new_layout`` across all layers.

        Returns the set of assignments that fall outside the new bounds.
        With ``dry_run=True`` nothing is changed -- callers use this to
        ask the user for confirmation first (FR-011).
        """
        new_gr, new_gc = grid_shape(new_layout, self.orientation)
        lost: set[LostAssignment] = set()
        for li, layer in enumerate(self.layers):
            for r, row in enumerate(layer.buttons):
                for c, action in enumerate(row):
                    if action is not None and (r >= new_gr or c >= new_gc):
                        lost.add(("button", li, r, c))
            for k, knob in enumerate(layer.knobs[new_layout.knobs:],
                                     start=new_layout.knobs):
                for part in KNOB_PARTS:
                    if knob.get(part) is not None:
                        lost.add(("knob", li, k, part))
        if dry_run:
            return lost

        for layer in self.layers:
            new_buttons = [[None] * new_gc for _ in range(new_gr)]
            for r in range(min(new_gr, len(layer.buttons))):
                for c in range(min(new_gc, len(layer.buttons[r]))):
                    new_buttons[r][c] = layer.buttons[r][c]
            layer.buttons = new_buttons
            del layer.knobs[new_layout.knobs:]
            while len(layer.knobs) < new_layout.knobs:
                layer.knobs.append(KnobBinding())
        self.layout = new_layout
        self.dirty = True
        return lost

    def set_layer_count(self, count: int, *, dry_run: bool = False) -> set[LostAssignment]:
        """Grow or shrink the layer list; returns assignments lost by shrinking."""
        if not MIN_LAYERS <= count <= MAX_LAYERS:
            raise ValueError(f"layers must be {MIN_LAYERS}..{MAX_LAYERS}, got {count}")
        lost: set[LostAssignment] = set()
        for li in range(count, len(self.layers)):
            layer = self.layers[li]
            for r, row in enumerate(layer.buttons):
                for c, action in enumerate(row):
                    if action is not None:
                        lost.add(("button", li, r, c))
            for k, knob in enumerate(layer.knobs):
                for part in KNOB_PARTS:
                    if knob.get(part) is not None:
                        lost.add(("knob", li, k, part))
        if dry_run:
            return lost

        del self.layers[count:]
        gr, gc = self.grid_shape()
        while len(self.layers) < count:
            self.layers.append(Layer.empty(gr, gc, self.layout.knobs))
        self.dirty = True
        return lost

    def set_orientation(self, orientation: str) -> None:
        """Change orientation, transposing grids when the axis flips."""
        if orientation not in ORIENTATIONS:
            raise ValueError(f"unknown orientation {orientation!r}")
        if orientation == self.orientation:
            return
        was_horizontal = self.orientation in HORIZONTAL_ORIENTATIONS
        now_horizontal = orientation in HORIZONTAL_ORIENTATIONS
        if was_horizontal != now_horizontal:
            for layer in self.layers:
                layer.buttons = [list(row) for row in zip(*layer.buttons)]
        self.orientation = orientation
        self.dirty = True
