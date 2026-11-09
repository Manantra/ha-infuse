"""Keep current installation instructions and upstream API limitations discoverable."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / 'README.md').read_text()


def test_single_recovery_section_reflects_actual_rate_limit():
    coordinator = (ROOT / 'custom_components/infuse/coordinator.py').read_text()
    assert 'monotonic() - self._last_rediscovery < 15' in coordinator
    assert 'one attempt every 15 seconds per device' in README
    assert 'every 30 seconds' not in README
    assert README.count('## Connection recovery and troubleshooting') == 1
    for obsolete in (
        '## Automatic reconnection after Infuse is backgrounded',
        '## Bonjour port changes and Apple TV background behavior',
        '## Recovery after Infuse is backgrounded or restarted',
        '## HAOS virtual machines and stale Bonjour cache',
    ):
        assert obsolete not in README
    assert 'no_reachable_new_endpoint' in README
    assert 'directly for its DNS-SD SRV record' in README
    assert 'DNS-SD PTR records' in README


def test_infuse_profile_is_not_confused_with_tvos_user():
    assert 'active Infuse profile' in README
    assert 'Active Apple TV profile' not in README
    assert 'Infuse profiles should not be confused with tvOS users' in README


def test_firecore_api_issue_and_feature_request_linked_near_end():
    final_section = README.split('## Known Infuse API limitations and upstream reports', 1)[1]
    assert 'https://community.firecore.com/t/bug-now-playing-api-does-not-recover-after-returning-infuse-to-foreground-on-apple-tv/61240' in final_section
    assert 'https://community.firecore.com/t/expose-the-active-infuse-profile-via-the-now-playing-api/61239' in final_section
    assert 'not a second connection bug' in final_section
    assert 'open an integration issue with redacted diagnostics' in final_section
    assert 'MIT Licensed.' in final_section


def test_integration_is_the_only_installation_needed():
    assert 'Both cards are included in this integration' in README
    assert 'Do not install the old separate cards plugin' in README
    assert 'search for **Infuse Now Playing**' in README
