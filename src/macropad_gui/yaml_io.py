"""YAML load/save for ch57x-keyboard-tool configuration files.

Uses ruamel.yaml round-trip mode so that comments, key order, quoting and
unknown fields in hand-written files survive an open -> save cycle
(SC-003).  A loaded file's document object is cached on
``Config.yaml_doc`` and edits are written back into it; only cells whose
assignment actually changed are touched.  New configs are emitted from a
clean template that mirrors example-mapping.yaml's field order.
"""

from __future__ import annotations

import io
from pathlib import Path

import ruamel.yaml
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError

from .actions import UNASSIGNED, Action, ActionError, parse_action
from .model import (
    KEYBOARD_MODELS,
    KNOB_PARTS,
    MAX_COLUMNS,
    MAX_KNOBS,
    MAX_LAYERS,
    MAX_ROWS,
    MIN_COLUMNS,
    MIN_KNOBS,
    MIN_LAYERS,
    MIN_ROWS,
    ORIENTATIONS,
    Config,
    KnobBinding,
    Layer,
    Layout,
    grid_shape,
)


class ConfigFileError(Exception):
    """File unreadable, unparseable, or structurally wrong (FR-012)."""

    def __init__(self, message: str, line: int | None = None):
        self.message = message
        self.line = line
        if line is not None:
            message = f"line {line}: {message}"
        super().__init__(message)


class SchemaError(Exception):
    """A field value is outside the supported bounds (research R5)."""

    def __init__(self, field: str, value, allowed: str):
        self.field = field
        self.value = value
        self.allowed = allowed
        super().__init__(f"invalid {field}: {value!r} (allowed: {allowed})")


def _make_yaml() -> ruamel.yaml.YAML:
    yaml = ruamel.yaml.YAML()  # round-trip mode
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def _int_field(doc, name: str, lo: int, hi: int) -> int:
    if name not in doc:
        raise ConfigFileError(f"missing required field {name!r}")
    value = doc[name]
    if not isinstance(value, int) or isinstance(value, bool):
        raise SchemaError(name, value, f"integer {lo}..{hi}")
    if not lo <= value <= hi:
        raise SchemaError(name, value, f"{lo}..{hi}")
    return value


def _cell_action(value, where: str) -> Action | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigFileError(f"{where}: expected an action string, got {value!r}")
    if value == UNASSIGNED:
        return None
    try:
        return parse_action(value)
    except ActionError as e:
        raise ConfigFileError(f"{where}: invalid action {value!r}: {e.reason}")


def load(path) -> Config:
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as e:
        raise ConfigFileError(f"cannot read {path}: {e}")
    newline = "\r\n" if b"\r\n" in raw else "\n"
    try:
        text = raw.decode("utf-8").replace("\r\n", "\n")
        doc = _make_yaml().load(text)
    except (YAMLError, UnicodeDecodeError) as e:
        line = None
        mark = getattr(e, "problem_mark", None)
        if mark is not None:
            line = mark.line + 1
        raise ConfigFileError(f"not a valid YAML file: {e}", line)

    if not isinstance(doc, dict):
        raise ConfigFileError("top level of the file must be a mapping")

    model = doc.get("model")
    if model is not None:
        if model not in KEYBOARD_MODELS:
            raise SchemaError("model", model, " | ".join(KEYBOARD_MODELS))
    if "orientation" not in doc:
        raise ConfigFileError("missing required field 'orientation'")
    orientation = doc["orientation"]
    if orientation not in ORIENTATIONS:
        raise SchemaError("orientation", orientation, " | ".join(ORIENTATIONS))

    rows = _int_field(doc, "rows", MIN_ROWS, MAX_ROWS)
    columns = _int_field(doc, "columns", MIN_COLUMNS, MAX_COLUMNS)
    knobs = _int_field(doc, "knobs", MIN_KNOBS, MAX_KNOBS)
    layout = Layout(rows, columns, knobs)

    layers_doc = doc.get("layers")
    if not isinstance(layers_doc, list) or not layers_doc:
        raise ConfigFileError("missing or empty 'layers' list")
    if not MIN_LAYERS <= len(layers_doc) <= MAX_LAYERS:
        raise SchemaError("layers", len(layers_doc),
                          f"{MIN_LAYERS}..{MAX_LAYERS} layers")

    gr, gc = grid_shape(layout, orientation)
    layers: list[Layer] = []
    for li, layer_doc in enumerate(layers_doc, start=1):
        if not isinstance(layer_doc, dict):
            raise ConfigFileError(f"layer {li}: expected a mapping")
        buttons_doc = layer_doc.get("buttons")
        if not isinstance(buttons_doc, list) or len(buttons_doc) != gr:
            found = len(buttons_doc) if isinstance(buttons_doc, list) else 0
            raise ConfigFileError(
                f"layer {li}: expected {gr} button rows for this layout and "
                f"orientation, found {found}")
        buttons: list[list[Action | None]] = []
        for r, row_doc in enumerate(buttons_doc, start=1):
            if not isinstance(row_doc, list) or len(row_doc) != gc:
                found = len(row_doc) if isinstance(row_doc, list) else 0
                raise ConfigFileError(
                    f"layer {li} button row {r}: expected {gc} entries, "
                    f"found {found}")
            buttons.append([
                _cell_action(cell, f"layer {li} button row {r} column {c}")
                for c, cell in enumerate(row_doc, start=1)
            ])
        knobs_doc = layer_doc.get("knobs")
        if knobs_doc is None:
            knobs_doc = []
        if not isinstance(knobs_doc, list) or len(knobs_doc) != knobs:
            found = len(knobs_doc) if isinstance(knobs_doc, list) else 0
            raise ConfigFileError(
                f"layer {li}: expected {knobs} knob entries, found {found}")
        knob_bindings: list[KnobBinding] = []
        for k, knob_doc in enumerate(knobs_doc, start=1):
            if not isinstance(knob_doc, dict):
                raise ConfigFileError(f"layer {li} knob {k}: expected a mapping")
            binding = KnobBinding()
            for part in KNOB_PARTS:
                binding.set(part, _cell_action(
                    knob_doc.get(part), f"layer {li} knob {k} {part}"))
            knob_bindings.append(binding)
        layers.append(Layer(buttons=buttons, knobs=knob_bindings))

    return Config(
        layout=layout,
        layers=layers,
        model=model,
        orientation=orientation,
        source_path=path,
        dirty=False,
        yaml_doc=doc,
        newline=newline,
    )


# --------------------------------------------------------------------------
# Saving
# --------------------------------------------------------------------------


def _cell_text(action: Action | None) -> str:
    return action.text if action is not None else UNASSIGNED


def _existing_cell_value(value) -> str | None:
    """Semantic value of a YAML cell: None for unassigned (null or <0>)."""
    if value is None:
        return None
    text = str(value)
    return None if text == UNASSIGNED else text


def _flow_seq(items) -> CommentedSeq:
    seq = CommentedSeq(items)
    seq.fa.set_flow_style()
    return seq


def _build_layer(layer: Layer) -> CommentedMap:
    layer_doc = CommentedMap()
    layer_doc["buttons"] = CommentedSeq(
        _flow_seq([_cell_text(a) for a in row]) for row in layer.buttons)
    knobs_doc = CommentedSeq()
    for knob in layer.knobs:
        knob_doc = CommentedMap()
        for part in KNOB_PARTS:
            knob_doc[part] = _cell_text(knob.get(part))
        knobs_doc.append(knob_doc)
    layer_doc["knobs"] = knobs_doc
    return layer_doc


def _build_doc(config: Config) -> CommentedMap:
    doc = CommentedMap()
    if config.model is not None:
        doc["model"] = config.model
    doc["orientation"] = config.orientation
    doc["rows"] = config.layout.rows
    doc["columns"] = config.layout.columns
    doc["knobs"] = config.layout.knobs
    doc["layers"] = CommentedSeq(_build_layer(layer) for layer in config.layers)
    return doc


def _apply_scalar(doc: CommentedMap, key: str, value, insert_at: int) -> None:
    if value is None:
        doc.pop(key, None)
    elif key not in doc:
        doc.insert(insert_at, key, value)
    elif doc[key] != value:
        doc[key] = value


def _apply_layer(layer_doc, layer: Layer, gr: int, gc: int) -> None:
    buttons_doc = layer_doc.get("buttons")
    if (not isinstance(buttons_doc, list) or len(buttons_doc) != gr
            or any(not isinstance(row, list) or len(row) != gc
                   for row in buttons_doc)):
        layer_doc["buttons"] = CommentedSeq(
            _flow_seq([_cell_text(a) for a in row]) for row in layer.buttons)
    else:
        for r, row in enumerate(layer.buttons):
            for c, action in enumerate(row):
                new = action.text if action is not None else None
                if _existing_cell_value(buttons_doc[r][c]) != new:
                    buttons_doc[r][c] = _cell_text(action)

    knobs_doc = layer_doc.get("knobs")
    if (not isinstance(knobs_doc, list) or len(knobs_doc) != len(layer.knobs)
            or any(not isinstance(k, dict) for k in knobs_doc)):
        knobs_doc = CommentedSeq()
        for knob in layer.knobs:
            knob_doc = CommentedMap()
            for part in KNOB_PARTS:
                knob_doc[part] = _cell_text(knob.get(part))
            knobs_doc.append(knob_doc)
        layer_doc["knobs"] = knobs_doc
    else:
        for knob_doc, knob in zip(knobs_doc, layer.knobs):
            for part in KNOB_PARTS:
                action = knob.get(part)
                new = action.text if action is not None else None
                if _existing_cell_value(knob_doc.get(part)) != new:
                    knob_doc[part] = _cell_text(action)


def _apply_to_doc(doc: CommentedMap, config: Config) -> None:
    _apply_scalar(doc, "model", config.model, 0)
    _apply_scalar(doc, "orientation", config.orientation, 1)
    _apply_scalar(doc, "rows", config.layout.rows, 2)
    _apply_scalar(doc, "columns", config.layout.columns, 3)
    _apply_scalar(doc, "knobs", config.layout.knobs, 4)

    layers_doc = doc.get("layers")
    if not isinstance(layers_doc, list):
        doc["layers"] = CommentedSeq(
            _build_layer(layer) for layer in config.layers)
        return
    del layers_doc[len(config.layers):]
    while len(layers_doc) < len(config.layers):
        layers_doc.append(_build_layer(config.layers[len(layers_doc)]))
    gr, gc = config.grid_shape()
    for layer_doc, layer in zip(layers_doc, config.layers):
        if isinstance(layer_doc, dict):
            _apply_layer(layer_doc, layer, gr, gc)


def save(config: Config, path) -> None:
    path = Path(path)
    if config.yaml_doc is not None:
        _apply_to_doc(config.yaml_doc, config)
    else:
        config.yaml_doc = _build_doc(config)

    buffer = io.StringIO()
    _make_yaml().dump(config.yaml_doc, buffer)
    text = buffer.getvalue()
    if config.newline != "\n":
        text = text.replace("\n", config.newline)
    try:
        path.write_bytes(text.encode("utf-8"))
    except OSError as e:
        raise ConfigFileError(f"cannot write {path}: {e}")
    config.source_path = path
    config.dirty = False
