"""Check the contract needed for migration from HACS to Marketplace."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_marketplace_integration_repository_structure():
    hacs = json.loads((ROOT / 'hacs.json').read_text())
    manifest = json.loads((ROOT / 'custom_components/infuse/manifest.json').read_text())
    assert hacs['name'] == 'Infuse Now Playing'
    assert manifest['domain'] == 'infuse'
    assert manifest['version'] == '0.2.9'
    assert (ROOT / 'custom_components/infuse/__init__.py').is_file()
    assert (ROOT / 'custom_components/infuse/brand/icon.png').is_file()
    assert manifest['issue_tracker'].startswith('https://github.com/')
    assert 'hacs' not in manifest.get('dependencies', [])
    assert 'marketplace' not in manifest.get('dependencies', [])


def test_different_repository_for_card_plugin():
    readme = (ROOT / 'README.md').read_text()
    assert 'Manantra/ha-infuse-cards' in readme
    assert 'marketplace_repository/?owner=Manantra&repository=ha-infuse' in readme
    assert (ROOT / 'examples/www/infuse-now-playing-card.js').is_file()
    assert (ROOT / 'examples/www/infuse-household-card.js').is_file()
