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
> Independent community project; not affiliated with Firecore, Infuse or the Home Assistant project. Firecore's documented Now Playing API is **read-only** and does not expose remote playback transport controls or the active Infuse profile.

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

## Connection recovery and troubleshooting (Apple TV / Bonjour)

Infuse 8.5.9+ exposes a **read-only** `GET /nowplaying` HTTP endpoint on a **dynamic TCP port** advertised via Bonjour (`_infuse-np._tcp.local.`). On Apple TV, **tvOS may suspend Infuse and its HTTP service while the app is in the background**; a Bonjour announcement can remain cached even when the listener no longer responds. In that situation, Home Assistant correctly reports the media player as `unavailable`, not `idle`. The integration cannot keep Infuse running in the background or start Infuse's private HTTP listener.

**How automatic recovery works:**

- Regular HTTP polling continues even while a device is unavailable. During initial Bonjour setup, the integration resolves the current advertised endpoint instead of trusting a potentially stale discovery notification; manual host/port setup is supported too.
- Since **v0.2.5**, the integration has monitored service changes using Home Assistant's shared Bonjour instance and verified new ports before accepting them. It can also set up an offline device as `unavailable` at Home Assistant startup without discarding its config entry.
- When HTTP polling fails, the integration first checks cached and freshly resolved Bonjour records. Since **v0.2.7**, it can also query the **already paired device** directly for its DNS-SD SRV record over UDP 5353 (useful for HAOS VMs with stale or missing multicast records).
- Since **v0.2.10**, the integration watches service announcements for manually configured devices too and can ask that **same paired device** for DNS-SD PTR records if the service name changed. It only accepts a new host/port after a successful `/nowplaying` HTTP probe; it does **not** scan subnets, probe arbitrary ports or adopt unrelated devices. Failed recovery discovery is limited to **one attempt every 15 seconds per device**.

**If the player stays unavailable after you reopen Infuse:**

1. Open Infuse on Apple TV and check that **Settings → Playback → Now Playing API** is still enabled. Wait at least 15–30 seconds for polling and rediscovery. The selected API port may have changed.
2. Download diagnostics under **Settings → Devices & services → Infuse Now Playing → Download diagnostics**. Check `connected`, `active_port`, `last_bonjour_resolution`, `recovery_attempts`, `last_connection_error`, `last_successful_contact` and `service_name_changed`; device addresses and TMDB credentials are redacted. `no_reachable_new_endpoint` indicates that no usable HTTP endpoint was found by the available recovery methods.
3. If possible, test `http://<apple-tv-ip>:<active_port>/nowplaying` from another device on the same local network. A refused connection on the current advertised port points to an unreachable listener, not simply a missing Home Assistant entity. Firewalls, VM network isolation, and blocked direct unicast UDP 5353 can also prevent discovery.
4. **Known upstream behavior:** In our testing, disabling and re-enabling the Now Playing API in Infuse's settings while Infuse was in the foreground restored the connection **without restarting the app or Home Assistant**. Fully quitting and reopening Infuse is another workaround. The Home Assistant integration cannot remotely toggle or restart Infuse's HTTP service. See the [Firecore API recovery bug report](https://community.firecore.com/t/bug-now-playing-api-does-not-recover-after-returning-infuse-to-foreground-on-apple-tv/61240).

If a newly discovered device's setup dialog still displays an old port, update the integration, restart Home Assistant, and reopen the discovery confirmation so the current Bonjour endpoint is resolved. A temporary `unavailable` state while Infuse is in the background is expected; **remaining unavailable after Infuse returns to the foreground despite a working network** is the separately reported API recovery problem and is not necessarily an integration defect.

## What is and is not available

| Capability | Support |
|---|---|
| Local playback state, position and duration | Yes |
| Film and episode metadata | Yes |
| Multiple independently tracked devices | Yes |
| Optional TMDB posters | Yes |
| Automation events | Yes |
| Remote play/pause/seek/volume via Infuse API | No |
| Active Infuse profile via Now Playing API | No |
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

## Home Assistant branding

The integration includes a custom orange play emblem (not an official Firecore icon) as 256×256 and 512×512 brand assets in `custom_components/infuse/brand/` (`icon.png`, `icon@2x.png`, `logo.png`, `logo@2x.png`). Home Assistant 2026.3+ loads these directly and the built-in Marketplace can fetch branding from the published repository release. Legacy HACS 2.0.5 may still show **“Icon not available”** in its own catalog because its frontend uses the older brands CDN instead of locally packaged icons; this does not affect the integration icon under **Settings → Devices & services**. See [the existing HACS frontend bug](https://github.com/hacs/integration/issues/5402).

## TMDB token persistence and the empty password field

An existing TMDB API Read Access Token is stored in Home Assistant's **config entry options**, not in the integration's Python files. Upgrading this integration must not reset it. For security, the token input in **Configure** is always blank, even when a token has already been saved. Since v0.2.6, the options screen shows **✓ saved** or **✗ not saved** next to the TMDB token status, without exposing the credential. Saving the options with the token field blank or containing only spaces preserves the existing token; the explicit **Remove stored TMDB token** checkbox deletes it.

For additional verification, download the integration diagnostics: `tmdb_configured: true` means a non-empty token is stored. The diagnostic file intentionally never includes the token itself. If `tmdb_configured: false`, you can re-enter your TMDB API Read Access Token via **Configure**; the integration cannot retrieve a token that has actually been deleted from the Home Assistant config entry.

## Security and privacy

The local API uses unencrypted, unauthenticated HTTP. Never expose the endpoint to the internet. Core playback monitoring stays local; TMDB queries are optional. Home Assistant event and history records may contain playback details, so configure retention appropriately.

## Development and support

The independent Python parser/client suite includes multi-device simulation, but live Infuse / Home Assistant validation remains required. Please report reproducible issues in [GitHub Issues](https://github.com/Manantra/ha-infuse/issues).

- [Firecore's third-party API documentation](https://support.firecore.com/hc/en-us/articles/215090997-API-for-Third-Party-Apps-Services)
- [Home Assistant integration developer documentation](https://developers.home-assistant.io/)

## Known Infuse API limitations and upstream reports

**A player showing `unavailable` does not automatically mean that this Home Assistant integration is broken.** Playback monitoring depends on a reachable Infuse Now Playing HTTP endpoint. We track the following reports with Firecore:

- **[Now Playing API does not recover after returning Infuse to the foreground on Apple TV — bug report](https://community.firecore.com/t/bug-now-playing-api-does-not-recover-after-returning-infuse-to-foreground-on-apple-tv/61240):** After backgrounding, the HTTP listener may remain unreachable even when Infuse is open again. Our tests found that switching the Now Playing API off and on in Infuse's settings restores access. The integration retries and rediscovers ports, but it cannot restart an HTTP listener that Infuse has not restored. For diagnosis and workarounds, see [Connection recovery and troubleshooting](#connection-recovery-and-troubleshooting-apple-tv--bonjour).
- **[Expose the active Infuse profile via the Now Playing API — feature request](https://community.firecore.com/t/expose-the-active-infuse-profile-via-the-now-playing-api/61239):** The current API does not expose which **Infuse profile** is selected. This is a missing API capability, **not a second connection bug**. Infuse profiles should not be confused with tvOS users; the Household card only displays profile data when an external Home Assistant sensor provides it.

If the endpoint responds correctly but the integration still fails to update, please [open an integration issue with redacted diagnostics](https://github.com/Manantra/ha-infuse/issues). These upstream reports document limitations of Infuse's current API, not a blanket guarantee that every `unavailable` state has the same cause.

MIT Licensed. Infuse and Firecore are trademarks of their respective owners.
