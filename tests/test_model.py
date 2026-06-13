"""Model tests: resize loss detection, dirty flag, knob defaults,
unassigned None <-> <0> round-trip semantics."""

import pytest

from macropad_gui.actions import parse_action
from macropad_gui.model import Config, KnobBinding, Layer, Layout
from macropad_gui import yaml_io


def _assign(config, layer, r, c, text):
    config.layers[layer].buttons[r][c] = parse_action(text)


def test_layout_bounds():
    Layout(1, 1, 0)
    Layout(8, 8, 4)
    with pytest.raises(ValueError):
        Layout(0, 4, 2)
    with pytest.raises(ValueError):
        Layout(3, 9, 2)
    with pytest.raises(ValueError):
        Layout(3, 4, 5)


def test_new_config_shape():
    config = Config.new(3, 4, 2, layer_count=3)
    assert len(config.layers) == 3
    for layer in config.layers:
        assert len(layer.buttons) == 3
        assert all(len(row) == 4 for row in layer.buttons)
        assert all(cell is None for row in layer.buttons for cell in row)
        assert len(layer.knobs) == 2
    assert not config.dirty


def test_knob_binding_defaults():
    knob = KnobBinding()
    assert knob.ccw is None and knob.press is None and knob.cw is None
    action = parse_action("volumeup")
    knob.set("cw", action)
    assert knob.get("cw") is action
    with pytest.raises(ValueError):
        knob.get("sideways")


def test_resize_grow_keeps_everything():
    config = Config.new(2, 2, 1, layer_count=2)
    _assign(config, 0, 1, 1, "ctrl-c")
    config.layers[0].knobs[0].set("press", parse_action("mute"))
    lost = config.resize(Layout(4, 4, 2))
    assert lost == set()
    assert config.layers[0].buttons[1][1].text == "ctrl-c"
    assert config.layers[0].knobs[0].press.text == "mute"
    assert len(config.layers[0].knobs) == 2
    assert config.dirty


def test_resize_shrink_reports_losses_across_all_layers():
    config = Config.new(3, 4, 2, layer_count=2)
    _assign(config, 0, 0, 0, "a")          # stays
    _assign(config, 0, 2, 3, "b")          # lost (row+col out of bounds)
    _assign(config, 1, 0, 2, "c")          # lost on layer 2 (column 3)
    config.layers[1].knobs[1].set("ccw", parse_action("volumedown"))  # lost knob

    # dry run reports without changing anything
    lost = config.resize(Layout(2, 2, 1), dry_run=True)
    assert lost == {
        ("button", 0, 2, 3),
        ("button", 1, 0, 2),
        ("knob", 1, 1, "ccw"),
    }
    assert config.layout == Layout(3, 4, 2)
    assert config.layers[0].buttons[2][3] is not None

    # real resize discards out-of-bounds, keeps the rest
    assert config.resize(Layout(2, 2, 1)) == lost
    assert config.layout == Layout(2, 2, 1)
    assert config.layers[0].buttons[0][0].text == "a"
    assert len(config.layers[0].buttons) == 2
    assert all(len(row) == 2 for row in config.layers[0].buttons)
    assert len(config.layers[1].knobs) == 1


def test_set_layer_count():
    config = Config.new(2, 2, 1, layer_count=3)
    _assign(config, 2, 0, 0, "x")
    lost = config.set_layer_count(2, dry_run=True)
    assert lost == {("button", 2, 0, 0)}
    assert len(config.layers) == 3
    assert config.set_layer_count(2) == lost
    assert len(config.layers) == 2
    assert config.set_layer_count(3) == set()
    assert config.layers[2].buttons[0][0] is None


def test_dirty_toggling(tmp_path):
    config = Config.new(2, 2, 1, layer_count=1)
    assert not config.dirty
    config.resize(Layout(2, 3, 1))
    assert config.dirty
    yaml_io.save(config, tmp_path / "out.yaml")
    assert not config.dirty


def test_unassigned_none_round_trips_as_placeholder(tmp_path):
    """None serializes as <0>; <0> deserializes back to None (R6)."""
    config = Config.new(2, 2, 1, layer_count=1)
    _assign(config, 0, 0, 1, "ctrl-c")
    path = tmp_path / "rt.yaml"
    yaml_io.save(config, path)

    text = path.read_text(encoding="utf-8")
    assert text.count("<0>") > 0  # unassigned positions written as no-op

    loaded = yaml_io.load(path)
    assert loaded.layers[0].buttons[0][0] is None
    assert loaded.layers[0].buttons[0][1].text == "ctrl-c"
    assert loaded.layers[0].knobs[0].press is None


def test_orientation_flip_transposes_grid():
    config = Config.new(2, 3, 0, layer_count=1)
    _assign(config, 0, 0, 2, "a")
    config.set_orientation("clockwise")
    assert config.grid_shape() == (3, 2)
    assert config.layers[0].buttons[2][0].text == "a"
    config.set_orientation("normal")
    assert config.layers[0].buttons[0][2].text == "a"
