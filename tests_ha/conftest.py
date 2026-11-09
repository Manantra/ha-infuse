"""Run separate smoke tests with real Home Assistant Core pytest fixtures.

This directory intentionally does not inherit the dependency-light test doubles
from tests/conftest.py. Run with pytest-homeassistant-custom-component installed.
"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def enable_integration(enable_custom_integrations):
    """Allow Home Assistant to load our local custom_components/infuse."""
    return
