"""YAML I/O tests: golden round-trip of example-mapping.yaml, schema
errors, malformed-file errors, single-edit fidelity."""

import pytest

from macropad_gui.actions import parse_action
from macropad_gui import yaml_io
from macropad_gui.yaml_io import ConfigFileError, SchemaError


def test_golden_round_trip_is_byte_identical(example_yaml_path, tmp_path):
    """Load the heavily commented example file and save it untouched:
    comments, key order, quoting and line endings must survive
    byte-for-byte (SC-003)."""
    config = yaml_io.load(example_yaml_path)
    out = tmp_path / "round-trip.yaml"
    yaml_io.save(config, out)
    assert out.read_bytes() == example_yaml_path.read_bytes()


def test_example_file_contents(example_yaml_path):
    config = yaml_io.load(example_yaml_path)
    assert config.model == "ch57x-2"
    assert config.orientation == "normal"
    assert config.layout.rows == 3
    assert config.layout.columns == 4
    assert config.layout.knobs == 2
    assert len(config.layers) == 3
    assert config.layers[0].buttons[0][1].text == "ctrl-a"
    assert config.layers[0].buttons[2][0].text == "<100>"
    assert config.layers[0].knobs[0].ccw.text == "wheelup"
    assert config.layers[2].knobs[0].press.text == "mute"
    assert not config.dirty
    assert config.source_path == example_yaml_path


def test_single_edit_changes_single_line(example_yaml_path, tmp_path):
    """Changing one assignment must leave every other line untouched."""
    config = yaml_io.load(example_yaml_path)
    config.layers[0].buttons[1][1] = parse_action("ctrl-shift-x")
    out = tmp_path / "edited.yaml"
    yaml_io.save(config, out)

    original = example_yaml_path.read_text(encoding="utf-8").splitlines()
    edited = out.read_text(encoding="utf-8").splitlines()
    assert len(original) == len(edited)
    diffs = [(a, b) for a, b in zip(original, edited) if a != b]
    assert len(diffs) == 1
    assert '"f"' in diffs[0][0]
    assert "ctrl-shift-x" in diffs[0][1]


def test_schema_error_for_too_many_knobs(tmp_path):
    bad = tmp_path / "bad-knobs.yaml"
    bad.write_text(
        "orientation: normal\nrows: 1\ncolumns: 1\nknobs: 9\n"
        "layers:\n  - buttons:\n      - [\"a\"]\n    knobs: []\n",
        encoding="utf-8",
    )
    with pytest.raises(SchemaError) as excinfo:
        yaml_io.load(bad)
    assert excinfo.value.field == "knobs"
    assert excinfo.value.value == 9


def test_schema_error_for_unknown_orientation(tmp_path):
    bad = tmp_path / "bad-orientation.yaml"
    bad.write_text(
        "orientation: sideways\nrows: 1\ncolumns: 1\nknobs: 0\n"
        "layers:\n  - buttons:\n      - [\"a\"]\n    knobs: []\n",
        encoding="utf-8",
    )
    with pytest.raises(SchemaError) as excinfo:
        yaml_io.load(bad)
    assert excinfo.value.field == "orientation"


def test_config_file_error_for_malformed_yaml(tmp_path):
    bad = tmp_path / "broken.yaml"
    bad.write_text("rows: [unclosed\ncolumns: 4\n", encoding="utf-8")
    with pytest.raises(ConfigFileError):
        yaml_io.load(bad)


def test_config_file_error_for_missing_file(tmp_path):
    with pytest.raises(ConfigFileError):
        yaml_io.load(tmp_path / "does-not-exist.yaml")


def test_config_file_error_for_invalid_action(tmp_path):
    bad = tmp_path / "bad-action.yaml"
    bad.write_text(
        "orientation: normal\nrows: 1\ncolumns: 1\nknobs: 0\n"
        "layers:\n  - buttons:\n      - [\"ctrl-bogus\"]\n    knobs: []\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigFileError) as excinfo:
        yaml_io.load(bad)
    assert "bogus" in str(excinfo.value)


def test_config_file_error_for_grid_mismatch(tmp_path):
    bad = tmp_path / "bad-grid.yaml"
    bad.write_text(
        "orientation: normal\nrows: 2\ncolumns: 2\nknobs: 0\n"
        "layers:\n  - buttons:\n      - [\"a\", \"b\"]\n    knobs: []\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigFileError) as excinfo:
        yaml_io.load(bad)
    assert "button rows" in str(excinfo.value)


def test_fresh_config_save_passes_own_loader(tmp_path):
    """A config built in the GUI saves to a file our loader accepts."""
    from macropad_gui.model import Config

    config = Config.new(3, 4, 2, layer_count=3, model="ch57x-2")
    config.layers[0].buttons[0][0] = parse_action("ctrl-c")
    config.layers[0].knobs[0].cw = parse_action("volumeup")
    out = tmp_path / "fresh.yaml"
    yaml_io.save(config, out)

    loaded = yaml_io.load(out)
    assert loaded.model == "ch57x-2"
    assert loaded.layout.rows == 3
    assert loaded.layers[0].buttons[0][0].text == "ctrl-c"
    assert loaded.layers[0].knobs[0].cw.text == "volumeup"
    assert len(loaded.layers) == 3


def test_unknown_extra_fields_preserved(tmp_path):
    """Hand-written extras the GUI doesn't model must survive a save."""
    src = tmp_path / "extra.yaml"
    src.write_text(
        "# my note\nmycustomfield: keepme\norientation: normal\n"
        "rows: 1\ncolumns: 1\nknobs: 0\n"
        "layers:\n  - buttons:\n      - [\"a\"]\n    knobs: []\n",
        encoding="utf-8",
    )
    config = yaml_io.load(src)
    config.layers[0].buttons[0][0] = parse_action("b")
    out = tmp_path / "extra-out.yaml"
    yaml_io.save(config, out)
    text = out.read_text(encoding="utf-8")
    assert "# my note" in text
    assert "mycustomfield: keepme" in text
