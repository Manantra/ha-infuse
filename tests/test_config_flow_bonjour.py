"""Ensure a config flow never confirms a port captured at initial discovery."""

import ast
from pathlib import Path


def test_confirmation_always_resolves_service_before_testing_connection():
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / "custom_components/infuse/config_flow.py").read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "InfuseConfigFlow")
    confirm = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "async_step_confirm")
    calls = [n for n in ast.walk(confirm) if isinstance(n, ast.Call)]
    lookups = [c for c in calls if isinstance(c.func, ast.Name) and c.func.id == "async_resolve_endpoint"]
    assert len(lookups) == 1
    assert any(kw.arg == 'fresh' and isinstance(kw.value, ast.Constant) and kw.value.value is True for kw in lookups[0].keywords)
    assert any(isinstance(c.func, ast.Attribute) and c.func.attr == '_test_connection' for c in calls)
