<p align="center"><img src="https://raw.githubusercontent.com/Manantra/ha-infuse/main/assets/infuse-home-assistant.svg" alt="Infuse Now Playing" width="850"></p>

<h1 align="center">Infuse Now Playing for Home Assistant</h1>

<p align="center"><strong>See what is playing. Make your home react.</strong><br>Local playback monitoring for Infuse, designed for Home Assistant.</p>

<p align="center">
<a href="https://github.com/Manantra/ha-infuse/actions/workflows/test.yml"><img alt="Validation" src="https://github.com/Manantra/ha-infuse/actions/workflows/test.yml/badge.svg"></a>
<a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-ef993c"></a>
<a href="https://www.home-assistant.io/"><img alt="Home Assistant" src="https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-41BDF5"></a>
</p>

**Infuse Now Playing** brings Firecore's local, read-only playback information to Home Assistant. Each Infuse endpoint is monitored independently, enabling accurate status and automations in households using multiple Apple TVs, iPads or other supported devices.

> [!IMPORTANT]
> Independent community project; not affiliated with Firecore, Infuse or the Home Assistant project. Firecore's documented Now Playing API is **read-only** and does not expose remote playback transport controls or the active Apple TV profile.

## Highlights

- Automatic Bonjour / mDNS discovery of Infuse endpoints, with manual host and port setup.
- Dedicated read-only media player, playback progress and remaining-time sensors per device.
- Independent playback sessions for multiple Infuse instances using the same account.
- Film and episode metadata and optional TMDB poster enrichment.
- Home Assistant automation events for playback and media transitions.
- Optional Infuse-inspired Lovelace cards for single-player and household views.
- Firecore library and stream URL-generation actions.

## Requirements

Infuse **8.5.9+** with **Settings → Playback → Now Playing API** enabled, a reachable local network and a compatible Home Assistant installation. The Infuse API port is dynamically assigned; Bonjour discovery is recommended.

## Installation

### HACS custom repository

In HACS, add `https://github.com/Manantra/ha-infuse` as a custom repository of type **Integration**. Download **Infuse Now Playing**, restart Home Assistant, and use **Settings → Devices & services → Add integration**.

### Manual installation

Copy `custom_components/infuse` to `<config>/custom_components/infuse`, restart Home Assistant, then add **Infuse Now Playing** under **Settings → Devices & services**.

The custom dashboard cards are optional. Their JavaScript files are in `examples/www/`; install them to `<config>/www/` and register each `/local/*.js` resource as a JavaScript module.

### Optional information tiles in the Infuse Now Playing dashboard card

The single-device **Infuse Now Playing** card has three independently configurable bottom information tiles: **Status**, **Progress**, and **Time remaining**. They are all enabled by default, so existing cards look unchanged. In the card's visual dashboard editor, use the three checkboxes under **Show bottom info tiles** (German: **Untere Infokacheln anzeigen**). You can also set the corresponding YAML options to `false`:

```yaml
type: custom:infuse-now-playing-card
entity: media_player.apple_tv_infuse_player
title: Apple TV Wohnzimmer
show_status: false
show_progress: true
show_remaining: false
```

The settings only control the **three bottom tiles**: the large playback status label (for example, *Pausiert*), cover, title, progress bar, and time indicators stay visible. When all three bottom tiles are disabled, their entire row is removed and the card becomes more compact. The options are display-only and do not alter the media-player entity or connection recovery.

**Existing installation:** The custom card JS is not automatically copied by HACS, because it is an optional example outside the integration folder. After updating, replace `<config>/www/infuse-now-playing-card.js` with the newer `examples/www/infuse-now-playing-card.js` from this repository. Make sure `/local/infuse-now-playing-card.js` is registered as a **JavaScript module** in your dashboard resources; reload the browser/dashboard (or update the resource URL with a version query parameter) if the old card remains cached. You do not need to re-add the Infuse device or change your TMDB token.

## What is and is not available

| Capability | Support |
|---|---|
| Local playback state, position and duration | Yes |
| Film and episode metadata | Yes |
| Multiple independently tracked devices | Yes |
| Optional TMDB posters | Yes |
| Automation events | Yes |
| Remote play/pause/seek/volume via Infuse API | No |
| Active Apple TV profile via Infuse API | No |
| Full Infuse library access | No |

A shared iCloud or Infuse account does not merge devices or playback sessions. The API does not provide active profile information, so the integration never invents or infers user identities.

## Optional TMDB poster setup during device installation

Both the automatic Bonjour confirmation and manual setup screen now include an **optional password-masked TMDB API Read Access Token** input. If you want movie and series covers, paste your own token from [TMDB account settings](https://www.themoviedb.org/settings/api) while adding the device. If you leave it blank, local playback status, titles and progress still work; posters can be enabled later under **Configure**. Each Infuse device keeps its own optional TMDB token in the Home Assistant entry options, separate from its local connection settings. No token is included in diagnostics.

## Episode titles and optional posters

Home Assistant's media-player card displays the **episode title** as its main title and the **series name + season/episode number** underneath (for example, **Zurückgelassen** / **Reign S1E7**). The metadata remains available as `media_title`, `media_series_title`, `media_season`, and `media_episode` attributes.

**Why is the cover missing?** The local Infuse Now Playing API provides media IDs but not cover images. Poster enrichment therefore uses the separate, optional [TMDB API](https://www.themoviedb.org/settings/api). To enable it:

1. Create or sign in to a free TMDB account and obtain an **API Read Access Token** from account settings under **API**.
2. Open **Home Assistant → Settings → Devices & services → Infuse Now Playing → Configure**.
3. Paste the **API Read Access Token** into the TMDB token field, save, and play a film or episode. Home Assistant will refresh the integration and request a poster when TMDB has one.

This is the **API Read Access Token**, not your TMDB password. No token is required to use playback status, series names or progress. Enabling artwork sends the TMDB media ID to TMDB; without a token, playback monitoring stays local. A movie poster or TV-series poster is shown when one is available. A missing TMDB ID, unavailable poster, invalid token or TMDB network error leaves the cover empty rather than breaking local playback.

## Bonjour port changes and Apple TV background behavior

Infuse allocates its local Now Playing API port dynamically. When configuring a Bonjour-discovered device, the integration actively resolves the current service address instead of trusting the original discovery notification. Configured devices attempt re-discovery on connection failures (at most once every 30 seconds) and automatically reconnect when Infuse resumes on a new port.

On Apple TV, the local HTTP endpoint may stop responding when Infuse is moved to the background. In that situation the media player becomes **unavailable** rather than incorrectly reporting **idle**. The Bonjour advertisement can remain visible even while the HTTP server is suspended. Reopening Infuse may not always restore the server; fully closing and reopening the app can bring it back with a different port. These behaviors were observed in a local Apple TV test and may vary by tvOS / Infuse version.

If Home Assistant still shows an old port in an existing setup dialog, update the integration and restart Home Assistant before opening the discovery again. The confirmation screen will then re-resolve the service automatically.

## Home Assistant branding

The integration includes the original orange play emblem extracted from [`assets/infuse-home-assistant.svg`](assets/infuse-home-assistant.svg) as a 256×256 icon and a 512×512 high-resolution icon in `custom_components/infuse/brand/`. Home Assistant 2026.3 and newer read locally bundled integration brand icons; the design is not a Firecore official icon. Some HACS versions may still show a generic placeholder inside the HACS catalog even when the icon works in **Settings → Devices & services**.

## Recovery after Infuse is backgrounded or restarted

On Apple TV, tvOS can suspend the Infuse HTTP service when the app is in the background. The mDNS advertisement may stay visible even if the service no longer answers HTTP requests. When the app is reopened, Infuse often allocates a new port; Home Assistant must follow that change without requiring you to delete the device, reload the integration or restart Home Assistant.

From version **0.2.5**, the integration listens to Infuse service changes through **Home Assistant's shared Bonjour instance**, updates the player endpoint when a new SRV port is advertised and refreshes the entities. When HTTP polling fails, it first tries the shared Bonjour instance and then a fresh resolver if the shared record is stale, limiting repeated lookups while the app is suspended. It also loads an already configured device as **unavailable** at Home Assistant startup if Infuse is still offline; regular polling and Bonjour monitoring continue until the service comes back.

You can inspect **Settings → Devices & services → Infuse Now Playing → Download diagnostics** to see the original setup port, active port, port-switch count, and last resolution path. Addresses and TMDB credentials remain redacted. If the HTTP service remains unreachable even on the most recent Bonjour port, completely quit and reopen Infuse on the Apple TV; Home Assistant cannot restart Infuse's local listener itself.

## TMDB token persistence and the empty password field

An existing TMDB API Read Access Token is stored in Home Assistant's **config entry options**, not in the integration's Python files. Upgrading this integration must not reset it. For security, the token input in **Configure** is always blank, even when a token has already been saved. Since v0.2.6, the options screen shows **✓ saved** or **✗ not saved** next to the TMDB token status, without exposing the credential. Saving the options with the token field blank or containing only spaces preserves the existing token; the explicit **Remove stored TMDB token** checkbox deletes it.

For additional verification, download the integration diagnostics: `tmdb_configured: true` means a non-empty token is stored. The diagnostic file intentionally never includes the token itself. If `tmdb_configured: false`, you can re-enter your TMDB API Read Access Token via **Configure**; the integration cannot retrieve a token that has actually been deleted from the Home Assistant config entry.

## HAOS virtual machines and stale Bonjour cache (v0.2.7)

In some Home Assistant OS virtual-machine networks, Home Assistant continues reporting an **old Infuse API port** even after the Apple TV has restarted its local HTTP listener. A fresh multicast query may also fail because mDNS delivery through the VM bridge is inconsistent. Version 0.2.7 adds one more targeted fallback: when HTTP polling and the shared/fresh Bonjour resolvers cannot find a reachable updated port, the integration sends a single **unicast DNS-SD SRV query directly to the already configured Apple TV on UDP 5353**. This requests its current `_infuse-np._tcp.local.` port and verifies the returned port by successfully reading the HTTP `/nowplaying` endpoint before accepting it. No subnet scan, arbitrary HTTP port scan or other-device discovery occurs. Queries remain throttled and only run when existing HTTP polling fails.

Bonjour service-change events are also validated with an HTTP read before switching ports, so stale cached events cannot replace a working endpoint. The integration diagnostic `last_bonjour_resolution` value `direct_unicast` indicates the new recovery route was used. If a router, firewall or virtualization layer blocks direct unicast UDP 5353, the integration falls back to its existing discovery behavior and remains unavailable until Infuse can actually be reached.

## Security and privacy

The local API uses unencrypted, unauthenticated HTTP. Never expose the endpoint to the internet. Core playback monitoring stays local; TMDB queries are optional. Home Assistant event and history records may contain playback details, so configure retention appropriately.

## Development and support

The independent Python parser/client suite includes multi-device simulation, but live Infuse / Home Assistant validation remains required. Please report reproducible issues in [GitHub Issues](https://github.com/Manantra/ha-infuse/issues).

- [Firecore's third-party API documentation](https://support.firecore.com/hc/en-us/articles/215090997-API-for-Third-Party-Apps-Services)
- [Home Assistant integration developer documentation](https://developers.home-assistant.io/)

MIT Licensed. Infuse and Firecore are trademarks of their respective owners.