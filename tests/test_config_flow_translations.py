"""Regression checks for Bonjour discovery confirmation translations.

The integration's small dependency-free test suite verifies the flow contract
without importing a complete Home Assistant installation.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from string import Formatter


ROOT = Path(__file__).resolve().parents[1] / 'custom_components' / 'infuse'


def _confirm_form_call() -> ast.Call:
    module = ast.parse((ROOT / 'config_flow.py').read_text())
    flow = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == 'InfuseConfigFlow')
    method = next(n for n in flow.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'async_step_confirm')
    calls = (
        n for n in ast.walk(method)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'async_show_form'
    )
    return next(c for c in calls if any(k.arg == 'step_id' and isinstance(k.value, ast.Constant) and k.value.value == 'confirm' for k in c.keywords))


def test_discovery_confirmation_passes_translation_values() -> None:
    """A title with {name} must receive its interpolation arguments."""
    call = _confirm_form_call()
    placeholders = next(k.value for k in call.keywords if k.arg == 'description_placeholders')
    assert isinstance(placeholders, ast.Dict)
    assert {k.value for k in placeholders.keys} == {'name', 'host', 'port'}
    values = {k.value: ast.unparse(v) for k, v in zip(placeholders.keys, placeholders.values)}
    assert 'self._discovered[CONF_NAME]' in values['name']
    assert 'self._discovered[CONF_HOST]' in values['host']
    assert 'self._discovered[CONF_PORT]' in values['port']


def test_all_translations_receive_placeholders() -> None:
    """All localized confirmation title/description variables are provided."""
    for relpath in ('strings.json', 'translations/en.json', 'translations/de.json'):
        data = json.loads((ROOT / relpath).read_text())
        confirm = data['config']['step']['confirm']
        for key in ('title', 'description'):
            placeholders = {name for _, name, _, _ in Formatter().parse(confirm[key]) if name}
            assert placeholders <= {'name', 'host', 'port'}, (relpath, key, placeholders)
        assert '{name}' in confirm['title']
        assert '{host}:{port}' in confirm['description']
