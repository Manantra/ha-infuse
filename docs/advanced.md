# Advanced setup and options

[← Back to README](../README.md) · [Troubleshooting](troubleshooting.md) · [Migration](migration.md)

These options are **not required** for a normal Marketplace/HACS setup.

## Reconfigure an existing Infuse device

If an Apple TV's host/IP address or manually entered Now Playing API port changes, open **Settings → Devices & services → Infuse Now Playing**, select the device and choose **Reconfigure** from its menu. With Infuse open and its API enabled, enter the current host and port; Home Assistant validates the new endpoint before saving.

The existing config entry, entity IDs, dashboard cards, automations, polling options, and stored TMDB token are preserved. Reconfigure does not attempt to identify a different physical device: the read-only API provides no stable hardware ID. Check the address carefully. A manual host change clears the old Bonjour service-name binding to avoid reassociating the entry with an earlier device. Ordinary port changes should normally recover automatically, so Reconfigure is rarely necessary.

## Card visual editor and YAML options

The **Infuse Now Playing** single-device card provides a searchable media-player entity picker and three configurable bottom information tiles: **Status**, **Progress** and **Time remaining**. All are visible by default. Disable any of them in the visual card editor under **Show bottom info tiles** (German: **Untere Infokacheln anzeigen**), or configure the card in YAML:

```yaml
type: custom:infuse-now-playing-card
entity: media_player.apple_tv_infuse_player
title: Apple TV Wohnzimmer
show_status: false
show_progress: true
show_remaining: false
```

Only the three **bottom tiles** are affected. The main status, cover, title, progress bar and time information remain visible; hiding all three removes their row. These settings do not affect playback or connection handling.

The **Infuse Household** card's visual editor supports adding, removing and reordering players, choosing a title, and optionally assigning an **external Home Assistant profile sensor** per player. Infuse itself does not provide the active profile through its Now Playing API; external sensor information is labeled separately.

The card types are `custom:infuse-now-playing-card` and `custom:infuse-household-card`. A legacy card migration does not require editing existing YAML; see [Migration](migration.md).

## Dashboard resource registration

The integration serves `/api/infuse/cards/infuse-dashboard-cards.js` and automatically registers its versioned module in Home Assistant's **storage resource mode**. There is no need to copy JavaScript into `/config/www/` or install an additional plugin.

For `lovelace: resource_mode: yaml`, manually add one module entry in `configuration.yaml` (and remove obsolete Infuse card resources if you migrated from the old package):

```yaml
lovelace:
  resource_mode: yaml
  resources:
    - url: /api/infuse/cards/infuse-dashboard-cards.js?v=0.2.15
      type: module
```

**Update the `?v=` value to match your installed integration version after each upgrade** to avoid browser caching. If the visual editor appears outdated, refresh Home Assistant in your browser or app. The integration does not modify YAML resources.

## TMDB token, posters and episode metadata

Infuse's Now Playing API gives media metadata and IDs, but no artwork. To enable TMDB movie or TV posters, create a TMDB account and obtain its **API Read Access Token** from [TMDB API settings](https://www.themoviedb.org/settings/api). Enter it during Bonjour/manual device setup or under **Settings → Devices & services → Infuse Now Playing → Configure**. This is the **API Read Access Token**, not your TMDB account password.

The token is stored in Home Assistant **config entry options**, not inside the integration's Python files. The password-style token input stays blank even when a token is saved. The options screen shows **✓ saved** or **✗ not saved**; leaving the field blank keeps an existing token, while the explicit **Remove stored TMDB token** checkbox deletes it. Diagnostics expose only whether a token exists (`tmdb_configured`), not the secret itself.

With TMDB enabled, the media ID is sent to TMDB for artwork. Poster fetching happens independently of playback state updates and automation events; a missing ID, invalid token, absent poster or failed request leaves the cover empty without breaking local monitoring. Failed requests are temporarily cached, and the artwork cache is bounded.

For episodes, the media-player's main title is the **episode title**; the **series name + season/episode** appears underneath. Attributes include `media_title`, `media_series_title`, `media_season`, and `media_episode`.

## Manual installation

Copy `custom_components/infuse` from this repository to `<config>/custom_components/infuse` in your Home Assistant configuration, restart Home Assistant, then add **Infuse Now Playing** under **Settings → Devices & services**. The bundled cards live in `custom_components/infuse/www/`; do not copy them separately into `/config/www/`.

## Development, branding and compatibility notes

The integration includes its own orange icon and logos in `custom_components/infuse/brand/`; these are community assets, not official Firecore branding. If an older HACS catalog displays “Icon not available” while the integration still works, this may be a [legacy HACS frontend branding issue](https://github.com/hacs/integration/issues/5402).

Continuous integration runs Python regression tests, JavaScript card tests, HACS/hassfest checks, and a **separate smoke suite against real Home Assistant Core** with the Infuse HTTP endpoint mocked. The smoke suite verifies config-entry setup/unload, entity creation, offline startup, Lovelace resource registration, Reconfigure and discovery confirmation. To run it locally with Python 3.14 and pinned dependencies:

```bash
uv venv --python 3.14 .venv-ha
uv pip install --python .venv-ha/bin/python -r requirements-test-ha.txt
.venv-ha/bin/python -m pytest tests_ha -q
```

Live Infuse/tvOS testing is still needed for physical-device, LAN and background/foreground behavior. For design details see [Architecture](architecture.md), and for a version-by-version history see [Releases](https://github.com/Manantra/ha-infuse/releases).
