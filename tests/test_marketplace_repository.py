"""Check the contract needed for migration from HACS to Marketplace."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_marketplace_integration_repository_structure():
    hacs = json.loads((ROOT / 'hacs.json').read_text())
    manifest = json.loads((ROOT / 'custom_components/infuse/manifest.json').read_text())
    assert hacs['name'] == 'Infuse Now Playing'
    assert manifest['domain'] == 'infuse'
    assert list(manifest) == ['domain', 'name', *sorted(k for k in manifest if k not in ('domain', 'name'))]
    assert manifest['version'] == '0.2.11'
    assert (ROOT / 'custom_components/infuse/__init__.py').is_file()
    assert (ROOT / 'custom_components/infuse/brand/icon.png').is_file()
    assert manifest['issue_tracker'].startswith('https://github.com/')
    assert 'hacs' not in manifest.get('dependencies', [])
    assert 'marketplace' not in manifest.get('dependencies', [])


def test_bundled_card_repository_and_resource_contract():
    readme = (ROOT / 'README.md').read_text()
    manifest = json.loads((ROOT / 'custom_components/infuse/manifest.json').read_text())
    assert {'http', 'frontend', 'lovelace'} <= set(manifest['dependencies'])
    assert 'marketplace_repository/?owner=Manantra&repository=ha-infuse' in readme
    assert '/api/infuse/cards/infuse-dashboard-cards.js' in readme
    assert 'Migrating from the former separate cards repository' in readme
    bundled = ROOT / 'custom_components/infuse/www/infuse-dashboard-cards.js'
    assert bundled.is_file()
    source = bundled.read_text()
    assert 'class InfuseNowPlayingCard' in source
    assert 'class InfuseHouseholdCard' in source
    assert 'infuse-now-playing-card-editor' in source
    assert 'infuse-household-card-editor' in source
    assert 'custom:infuse-now-playing-card' in source
    assert 'type:"infuse-household-card"' in source
    assert not list((ROOT / 'examples/www').glob('*.js'))


def test_hassfest_friendly_translation_links_use_placeholders():
    for rel in ('strings.json', 'translations/en.json', 'translations/de.json'):
        data = json.loads((ROOT / 'custom_components/infuse' / rel).read_text())
        for namespace in ('config', 'options'):
            for step in data[namespace]['step'].values():
                assert 'https://' not in step.get('description', '')
                if '{tmdb_api_url}' in step.get('description', ''):
                    assert 'TMDB' in step['description']


def test_hassfest_friendly_config_entry_only_schema():
    init = (ROOT / 'custom_components/infuse/__init__.py').read_text()
    assert 'CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)' in init
