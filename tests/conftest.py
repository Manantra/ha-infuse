"""Import the dependency-free API modules without requiring Home Assistant."""

from importlib import import_module
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "infuse"
PACKAGE_NAME = "_infuse_api_tests"
package = ModuleType(PACKAGE_NAME)
package.__path__ = [str(ROOT)]
sys.modules.setdefault(PACKAGE_NAME, package)

model = import_module(f"{PACKAGE_NAME}.model")
links = import_module(f"{PACKAGE_NAME}.links")
api = import_module(f"{PACKAGE_NAME}.api")
metadata = import_module(f"{PACKAGE_NAME}.metadata")
