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

## Built-in Dashboard Cards — previews

**Both cards are included in this integration** (since **v0.2.11**). You do **not** need to install a second dashboard/plugin repository or copy JavaScript files to `/config/www`. On setup, Infuse Now Playing serves one versioned JavaScript module at `/api/infuse/cards/infuse-dashboard-cards.js` and automatically registers it as a Lovelace resource in **storage resource mode**.

| Single-device card | Household card (multiple devices) |
|:---:|:---:|
| ![Single Infuse device example: paused episode with cover and three configurable information tiles](https://raw.githubusercontent.com/Manantra/ha-infuse/main/assets/previews/single-device.png) | ![Infuse household example: three Apple TVs playing, paused and idle](https://raw.githubusercontent.com/Manantra/ha-infuse/main/assets/previews/multiple-devices.png) |

*Real card renderings with fictional example content.* The visual editors provide searchable Home Assistant entity pickers. The single-device card can hide/show the Status, Progress and Time remaining tiles; the Household card lets you add, remove and reorder players, choose a title, and optionally assign external HA profile sensors per player. An accessible **?** help bubble explains that Infuse's API cannot directly identify the current profile.

After installing the integration, edit a dashboard and add **Infuse Now Playing** or **Infuse Household** from the card picker. Their types remain `custom:infuse-now-playing-card` and `custom:infuse-household-card`; existing YAML/dashboard configuration needs no changes.

### Migrating from the former separate cards repository

The older [`ha-infuse-cards`](https://github.com/Manantra/ha-infuse-cards) package is superseded by the bundled version, in accordance with the HACS review guidance. **Existing users have a safe migration bridge**: the final separate cards **v0.1.4** release automatically imports the newer bundled JavaScript from this integration, with the original v0.1.3 card code as a fallback for outdated installations. No dashboard editing is needed, and **future card fixes and features then arrive whenever the Infuse integration is updated**, even while the old plugin is still installed.

**Easiest path — uninterrupted card updates:**

1. Update **Infuse Now Playing** to **v0.2.11 or later** and restart Home Assistant.
2. Update the **separate Infuse Dashboard Cards plugin** to its final **v0.1.4 (Legacy Bridge)** release through HACS/Marketplace. It is safe to keep that legacy resource installed for the moment; its bridge automatically loads the bundled cards from `/api/infuse/cards/infuse-dashboard-cards.js`.
3. Refresh the browser/app frontend. Both existing Lovelace card types now run the integrated version, including their visual editors and future card updates from this integration.

**Recommended final cleanup — only one installation:** After the bridge is active, uninstall the separate cards package through HACS/Marketplace and remove any leftover old cards resource entries under **Settings → Dashboards → Resources** (e.g. `/hacsfiles/ha-infuse-cards/`, `/local/community/ha-infuse-cards/`, `/local/infuse-now-playing-card.js`, `/local/infuse-household-card.js`). **Do not remove unrelated resources.** Reload the Infuse integration or restart Home Assistant. It will then register the new bundled `/api/infuse/cards/` resource itself. The integration intentionally does **not** delete or change HACS-managed resources, because HACS/Marketplace owns those entries.

**Important:** If you manually copied the old JavaScript to `/config/www/`, HACS cannot update those files. Remove their manually registered dashboard resource and follow the final cleanup above. Your original custom card **types, entity IDs, YAML configurations and automations stay the same**.

For setups with `lovelace: resource_mode: yaml`, automatic editing of `configuration.yaml` is intentionally disabled. Replace old card resource entries in `lovelace: resources:` with exactly one module resource:

```yaml
lovelace:
  resource_mode: yaml
  resources:
    - url: /api/infuse/cards/infuse-dashboard-cards.js?v=0.2.12
      type: module
```

Update the `?v=` value after future integration upgrades to bypass browser caching. The integration still serves the file automatically in YAML mode.

## Requirements

Infuse **8.5.9+** with **Settings → Playback → Now Playing API** enabled, a reachable local network and a compatible Home Assistant installation. The Infuse API port is dynamically assigned; Bonjour discovery is recommended.

## Installation

### Home Assistant 2026.11+ — Marketplace

Starting with **Home Assistant 2026.11** (released November 4, 2026), HACS is part of Home Assistant as the built-in **Marketplace**, found under **Settings → Marketplace**. Existing HACS installations and custom repositories migrate automatically on the first start after the Home Assistant update; you **do not need to reinstall Infuse or delete your existing config entry**. Home Assistant preserves your config entry options (including any TMDB token) and entity IDs.

**Recommended installation:** Open **Settings → Marketplace**, search for **Infuse Now Playing**, and install it from the integration catalog. The cards are included. Since the HACS catalog submission has been approved and merged, a custom repository is no longer the default route; catalog indexing may take some time to refresh.

**Alternative:** If it is not yet listed, choose **Marketplace → ⋮ → Custom repositories**, enter `https://github.com/Manantra/ha-infuse` as category **Integration**, and install it that way. This uses the same integration and does not require reinstalling any existing config entries.

[Open Infuse Now Playing in Marketplace](https://my.home-assistant.io/redirect/marketplace_repository/?owner=Manantra&repository=ha-infuse&category=integration) (Home Assistant 2026.11+).

**Dashboard cards are included.** The single-device and household cards are automatically served and registered by this integration. Do not install the old separate cards plugin; see the migration instructions above if you previously installed it.

### Home Assistant 2026.10 and older — HACS

Keep using HACS on older Home Assistant versions. In HACS, **search for Infuse Now Playing** in the integration catalog and install it, then restart Home Assistant and use **Settings → Devices & services → Add integration**. If the catalog result has not appeared yet, add `https://github.com/Manantra/ha-infuse` as a custom repository of type **Integration** instead. Both dashboard cards are included; no separate plugin is required.

### Manual installation

Copy `custom_components/infuse` to `<config>/custom_components/infuse`, restart Home Assistant, then add **Infuse Now Playing** under **Settings → Devices & services**.

The dashboard cards ship inside `custom_components/infuse/www/` and are registered on setup in resource storage mode. You no longer need to copy any card files into `<config>/www/` or manage a separate HACS cards package.

### Optional information tiles in the Infuse Now Playing dashboard card

The single-device **Infuse Now Playing** card uses Home Assistant's **searchable entity picker** in the visual editor (filtered to media players), plus three independently configurable bottom information tiles: **Status**, **Progress**, and **Time remaining**. They are all enabled by default, so existing cards look unchanged. In the card's visual dashboard editor, use the three checkboxes under **Show bottom info tiles** (German: **Untere Infokacheln anzeigen**). You can also set the corresponding YAML options to `false`:

```yaml
type: custom:infuse-now-playing-card
entity: media_player.apple_tv_infuse_player
title: Apple TV Wohnzimmer
show_status: false
show_progress: true
show_remaining: false
```

The settings only control the **three bottom tiles**: the large playback status label (for example, *Pausiert*), cover, title, progress bar, and time indicators stay visible. When all three bottom tiles are disabled, their entire row is removed and the card becomes more compact. The options are display-only and do not alter the media-player entity or connection recovery.

**Card updates:** Integration updates automatically update the bundled dashboard resource URL using the integration version. If the card editor appears outdated after upgrading, refresh the Home Assistant frontend cache. YAML resource users should update their `?v=` value manually, as described above.

## Automatic reconnection after Infuse is backgrounded

Infuse 8.5.9+ hosts a **read-only** `GET /nowplaying` API on a **temporary TCP port** advertised through Bonjour (`_infuse-np._tcp.local.`). **tvOS can suspend background apps and their HTTP listeners.** Therefore, the Home Assistant media player correctly becomes `unavailable` while no HTTP API is reachable; marking it `idle` would incorrectly imply that Infuse is online. This is not a permanent connection and it cannot keep an Apple TV app running in the background.

Starting with **v0.2.10**, the integration proactively restores its API connection after Infuse returns to the foreground whenever the device advertises or serves a reachable endpoint:

- Regular HTTP polling continues without restarting Home Assistant, even while offline.
- A Bonjour listener watches **all Infuse services** on the shared Home Assistant mDNS instance, including devices initially added **manually**. A renamed service is accepted only when it belongs to the original IP and returns a valid Infuse API response. No unrelated devices are automatically adopted.
- If the old port is unreachable, the integration checks the cached and fresh Bonjour record, then the already-paired device via targeted unicast DNS-SD. As a final fallback it asks that **same device** for currently advertised Infuse service names (PTR), even if the service name changed since initial setup. No subnet scanning or port sweeps are performed.
- A candidate endpoint is **tested before replacing** the last active endpoint, so stale records cannot overwrite it. Failed discovery is rate-limited to one attempt every 15 seconds per device.
- Diagnostics under **Settings → Devices & services → Infuse Now Playing → Download diagnostics** include `last_bonjour_resolution`, `recovery_attempts`, `last_connection_error`, `last_successful_contact` and `service_name_changed` (with host and credentials redacted).

**Limit:** If Infuse does not recreate or advertise a working Now Playing HTTP listener after returning to the foreground, no Home Assistant integration can restart that private server. A permanent fix for that specific case requires Firecore to repair its API lifecycle (especially foreground reactivation and re-announcement). The problem should be reported to Firecore separately from requests for additional API response fields, such as an active profile ID.

**How to diagnose:** Open Infuse, confirm the Now Playing API setting remains enabled, wait 15–30 seconds, and download the integration diagnostics. If `connected` stays false, `last_bonjour_resolution` reports `no_reachable_new_endpoint`, and Infuse is visible in the foreground, the logs help distinguish unavailable HTTP service from stale SRV records. When feasible, test `http://<apple-tv-ip>:<active_port>/nowplaying` from a device on the same LAN; a refused connection means the listener itself is not reachable on that advertised port. The API has no documented remote command to start its listener.

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

The integration includes a custom orange play emblem (not an official Firecore icon) as 256×256 and 512×512 brand assets in `custom_components/infuse/brand/` (`icon.png`, `icon@2x.png`, `logo.png`, `logo@2x.png`). Home Assistant 2026.3+ loads these directly and the built-in Marketplace can fetch branding from the published repository release. Legacy HACS 2.0.5 may still show **“Icon not available”** in its own catalog because its frontend uses the older brands CDN instead of locally packaged icons; this does not affect the integration icon under **Settings → Devices & services**. See [the existing HACS frontend bug](https://github.com/hacs/integration/issues/5402).

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