# Architecture

## Core data flow

Each Infuse Now Playing mDNS service is represented by one Home Assistant config entry, one asynchronous local HTTP client and one update coordinator. The coordinator retrieves a validated playback snapshot, updates the media-player and sensor entities, and emits transitions only when the snapshot changes.

The optional TMDB enrichment uses a user-provided API read access token to look up poster artwork. It is not required for playback monitoring.

## Device identity and accounts

Bonjour service instance names form unique IDs. Multiple devices remain independent even if they play the same media or use the same iCloud account. Dynamic service ports are refreshed by discovery. Manual host:port entries may require reconfiguration when the port changes.

The Firecore Now Playing API does not expose Apple TV profile identity or iCloud account identification. A profile can be displayed only if another independently verified Home Assistant entity provides that information; it is labeled external.

## Media player behavior

This is a read-only media player. It exposes media information, play/pause status and position, not unsupported control commands. Link-generation actions return device URL schemes that must be opened on the device, not posted to Infuse's HTTP endpoint.

## Safety

Firecore serves the local Now Playing API without HTTP authentication or transport encryption. Keep it on a trusted LAN. Never expose the endpoint publicly. Avoid recording private watched titles longer than necessary.

## Quality gates

The Python parser and HTTP client are tested using simulated endpoints, including a two-device concurrency scenario. JavaScript dashboard cards receive syntax checks. Live-device and full Home Assistant integration testing are needed to verify end-to-end compatibility.
