"""
Smoke test for Visibility SDK.

This test verifies that the package can be imported successfully,
which is a critical CI check to prevent exit code 5 (no tests collected).
"""

import pytest


def test_import_visibility():
    """Test that the visibility package can be imported."""
    import visibility
    assert hasattr(visibility, "__version__")
    assert visibility.__version__ == "0.1.0"


def test_import_tracker():
    """Test that the Visibility tracker class can be imported."""
    from visibility.tracker import Visibility
    assert Visibility is not None


def test_import_schemas():
    """Test that schema functions can be imported."""
    from visibility.schemas import get_openai_tool_schema, get_mcp_manifest
    assert callable(get_openai_tool_schema)
    assert callable(get_mcp_manifest)


def test_import_config():
    """Test that config class can be imported."""
    from visibility.config import VisibilityConfig
    assert VisibilityConfig is not None


def test_import_events():
    """Test that events module can be imported."""
    from visibility.events import create_event, EVENT_TYPES, LOG_LEVELS
    assert isinstance(EVENT_TYPES, list)
    assert isinstance(LOG_LEVELS, list)


@pytest.mark.parametrize("module_name", [
    "visibility",
    "visibility.tracker",
    "visibility.schemas",
    "visibility.config",
    "visibility.events",
    "visibility.storage",
    "visibility.plugins",
    "visibility.redact",
    "visibility.summary",
])
def test_module_imports(module_name):
    """Test that all core modules can be imported."""
    __import__(module_name)
