"""Keep onboarding short without losing essential setup and support instructions."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()
TROUBLESHOOTING = (ROOT / "docs/troubleshooting.md").read_text()
MIGRATION = (ROOT / "docs/migration.md").read_text()
ADVANCED = (ROOT / "docs/advanced.md").read_text()
ARCHITECTURE = (ROOT / "docs/architecture.md").read_text()


def test_readme_is_a_concise_user_onboarding_page():
    assert len(README.splitlines()) <= 110
    headings = re.findall(r"^## (.+)$", README, flags=re.MULTILINE)
    assert headings == [
        "Features", "Requirements", "Installation & setup",
        "Built-in dashboard cards", "Optional TMDB artwork",
        "Limitations, privacy & support",
    ]
    assert "Infuse 8.5.9 or newer" in README
    assert "Settings → Devices & services" in README
    assert "search for **Infuse Now Playing**" in README
    assert "Both cards are included in this integration" in README
    assert "Do not install the old separate cards plugin" in README
    assert "media player and sensors" in README.lower()
    assert "active Infuse profile" in README
    assert "read-only" in README
    assert "without authentication or encryption" in README
    assert "https://github.com/Manantra/ha-infuse/releases" in README
    assert "https://github.com/Manantra/ha-infuse/issues" in README
    assert "## Safety fixes" not in README
    assert "## Connection recovery and troubleshooting" not in README
    assert not re.search(r"^#{2,3} .*v0\.", README, flags=re.MULTILINE)


def test_all_local_document_links_point_to_real_files():
    for source in (ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))):
        content = source.read_text()
        for target in re.findall(r"\]\(([^)]+\.md(?:#[a-z0-9-]+)?)\)", content):
            file_path = target.split("#", 1)[0]
            assert (source.parent / file_path).is_file(), f"{source}: broken link to {target}"
    for name in ("troubleshooting.md", "migration.md", "advanced.md", "architecture.md"):
        assert (ROOT / "docs" / name).is_file()
        assert f"docs/{name}" in README or name == "architecture.md" and "docs/architecture.md" in README


def test_troubleshooting_covers_connection_recovery_without_flooding_readme():
    coordinator = (ROOT / "custom_components/infuse/coordinator.py").read_text()
    assert "monotonic() - self._last_rediscovery < 15" in coordinator
    assert "one attempt every 15 seconds per device" in TROUBLESHOOTING
    assert "DNS-SD SRV record" in TROUBLESHOOTING
    assert "PTR records" in TROUBLESHOOTING
    assert "no_reachable_new_endpoint" in TROUBLESHOOTING
    assert "Download diagnostics" in TROUBLESHOOTING
    assert "http://<apple-tv-ip>:<active_port>/nowplaying" in TROUBLESHOOTING
    assert "https://community.firecore.com/t/bug-now-playing-api-does-not-recover-after-returning-infuse-to-foreground-on-apple-tv/61240" in TROUBLESHOOTING
    assert "https://community.firecore.com/t/expose-the-active-infuse-profile-via-the-now-playing-api/61239" in TROUBLESHOOTING
    assert "Infuse profiles" not in README  # The distinction belongs in support docs.
    assert "tvOS user profile" in TROUBLESHOOTING


def test_migration_details_are_kept_outside_new_user_path():
    assert "https://github.com/Manantra/ha-infuse-cards" in MIGRATION
    assert "v0.1.4 (Legacy Bridge)" in MIGRATION
    for snippet in (
        "/hacsfiles/ha-infuse-cards/", "/local/community/ha-infuse-cards/",
        "/local/infuse-now-playing-card.js", "/local/infuse-household-card.js",
        "/api/infuse/cards/infuse-dashboard-cards.js",
        "resource_mode: yaml", "Do not delete unrelated resources",
    ):
        assert snippet in MIGRATION
    assert "Legacy Bridge" not in README


def test_advanced_options_and_dev_instructions_remain_accessible():
    for item in (
        "show_status: false", "show_progress: true", "show_remaining: false",
        "tmdb_configured", "Remove stored TMDB token", "Reconfigure",
        "resource_mode: yaml", "requirements-test-ha.txt",
    ):
        assert item in ADVANCED
    assert "?v=0.2.15" in MIGRATION  # YAML-only users manage versioned resource caching.
    assert "real Home Assistant Core" in ARCHITECTURE
    assert "tvOS" in ARCHITECTURE
