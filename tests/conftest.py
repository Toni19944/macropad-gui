import pathlib
import pytest


@pytest.fixture
def example_yaml_path() -> pathlib.Path:
    """Golden round-trip fixture.

    A byte-for-byte copy of ch57x-keyboard-tool's ``example-mapping.yaml``
    is vendored under ``tests/fixtures/`` so the suite is self-contained:
    the upstream tool clone is not part of this repository.
    """
    return pathlib.Path(__file__).parent / "fixtures" / "example-mapping.yaml"
