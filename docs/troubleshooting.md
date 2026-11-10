# Troubleshooting

[← Back to README](../README.md) · [Advanced setup](advanced.md) · [Report a problem](https://github.com/Manantra/ha-infuse/issues)

Most connection problems come down to Infuse not exposing its **Now Playing API** at the advertised address and port. This guide separates what you can check in Home Assistant from limitations of Infuse or the local network.

## The integration is discovered, but setup says “Infuse not reachable”

A discovery prompt can remain visible while an Apple TV is asleep or Infuse has been suspended. **Discovery does not guarantee the API is currently reachable.** Infuse advertises a **dynamic TCP port** through Bonjour (`_infuse-np._tcp.local.`), and an old advertisement may outlive the listener.

1. Open **Infuse → Settings → Playback → Now Playing API** and verify it is enabled.
2. Close the existing Home Assistant setup dialog, reopen the discovered device and confirm while Infuse is in the foreground. The confirmation process queries the already discovered device for its latest DNS-SD SRV port rather than relying only on cached Bonjour data.
3. If discovery is unavailable or still stale, use **Add integration → Infuse Now Playing** and manually enter the **current** IP/host and API port shown by Infuse. The port can change when Infuse restarts.
4. Confirm that Home Assistant can access the device on its local network. Firewall restrictions, HAOS virtual-machine networking and multicast/UDP 5353 filtering can interfere with discovery.

The integration validates `GET /nowplaying` before creating the entry. It does not scan your subnet, guess arbitrary ports or adopt unrelated devices. If the API itself is not listening, Home Assistant cannot start it remotely.

## The media player shows `unavailable`

On Apple TV, tvOS may suspend Infuse and its HTTP service in the background. A temporarily unavailable player does not necessarily indicate a failed installation. A stopped service is different from an `idle` playback state.

1. Reopen Infuse and check that **Now Playing API** remains enabled. Allow **15–30 seconds** for normal polling and rediscovery.
2. If it remains unavailable, try switching the Now Playing API **off and back on** in Infuse settings while the app is open. In testing, this restored a listener that did not recover automatically. Fully quitting and reopening Infuse may also help.
3. If necessary, verify `http://<apple-tv-ip>:<active_port>/nowplaying` from a device on the same LAN. A refused connection suggests the HTTP service is not listening at that endpoint; check the actual port again.
4. Download diagnostics in **Settings → Devices & services → Infuse Now Playing → Download diagnostics**. If the endpoint responds but Home Assistant still does not update, [open an issue](https://github.com/Manantra/ha-infuse/issues) and attach **redacted** diagnostics.

**Known Firecore-side issue:** Infuse's HTTP listener may remain unreachable after returning to the foreground. See the [Firecore API recovery report](https://community.firecore.com/t/bug-now-playing-api-does-not-recover-after-returning-infuse-to-foreground-on-apple-tv/61240). Home Assistant cannot remotely toggle that listener; port rediscovery is helpful only when a working endpoint exists.

## Diagnostics and automatic recovery details

Infuse Now Playing polls the read-only `GET /nowplaying` endpoint. It monitors Bonjour service changes and validates a new endpoint over HTTP before switching ports. It can also query the **already paired device** directly for its DNS-SD SRV record over UDP 5353, and query that same device for PTR records if a service instance has been renamed. The integration does **not** probe arbitrary devices or scan the network. When automatic discovery fails, recovery discovery is limited to **one attempt every 15 seconds per device**.

An offline device can remain configured and be represented as `unavailable`. The integration retains existing Home Assistant entities, configuration and automations rather than deleting and recreating the device.

Useful diagnostics include `connected`, `active_port`, `last_bonjour_resolution`, `recovery_attempts`, `last_connection_error`, `last_successful_contact`, `service_name_changed`, and `tmdb_configured`. `no_reachable_new_endpoint` means available recovery methods could not find a working HTTP listener. Credentials and device addresses are redacted from the integration's diagnostics.

## Dashboard cards not showing or still using an old version

The integration automatically serves both cards at `/api/infuse/cards/infuse-dashboard-cards.js` and registers the resource in **Lovelace storage resource mode**. Refresh the Home Assistant browser/app cache after an update if the card editor looks outdated.

If you previously installed the **separate** `ha-infuse-cards` package, use the [migration guide](migration.md). Users managing `lovelace: resources:` in YAML must update their resource URL themselves; see [Advanced setup](advanced.md). Do **not** remove unrelated dashboard resources.

## Covers not appearing

TMDB artwork is optional. Verify that a TMDB **API Read Access Token** is saved under **Configure** and that Infuse provides a TMDB media ID for the title. An unavailable poster, invalid token, missing media ID or TMDB network error should not prevent local playback monitoring.

The token input may appear blank even with a token saved (for security); the status beside it tells you whether one is stored. See [Advanced setup](advanced.md).

## Other known API limits

The API does not expose the **active Infuse profile**. This is not a connection failure and should not be confused with a tvOS user profile. Track the request in the [Firecore profile feature thread](https://community.firecore.com/t/expose-the-active-infuse-profile-via-the-now-playing-api/61239).

For development and version-by-version fixes, see [GitHub Releases](https://github.com/Manantra/ha-infuse/releases) rather than relying on old troubleshooting instructions.
