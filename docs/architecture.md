# Architecture

## Core data flow

Each Infuse Now Playing mDNS service is represented by one Home Assistant config entry, one asynchronous local HTTP client and one update coordinator. The coordinator retrieves a validated playback snapshot, updates the media-player and sensor entities, and emits transitions only when the snapshot changes.

The optional TMDB enrichment uses a user-provided API read access token to look up poster artwork **asynchronously**, without blocking playback updates or automation events. It is not required for playback monitoring.

## Device identity and accounts

Bonjour service instance names form unique IDs. Multiple devices remain independent even if they play the same media or use the same iCloud account. Dynamic service ports are refreshed by discovery. Manual host:port entries may require reconfiguration when the port changes.

The Firecore Now Playing API does not expose Apple TV profile identity or iCloud account identification. A profile can be displayed only if another independently verified Home Assistant entity provides that information; it is labeled external.

## Media player behavior

This is a read-only media player. It exposes media information, play/pause status and position, not unsupported control commands. Link-generation actions return device URL schemes that must be opened on the device, not posted to Infuse's HTTP endpoint.

## Safety

Firecore serves the local Now Playing API without HTTP authentication or transport encryption. Keep it on a trusted LAN. Never expose the endpoint publicly. Avoid recording private watched titles longer than necessary.

## Quality gates

The Python parser, HTTP client, Bonjour discovery and coordinator are covered by regression tests, including multi-device scenarios. Dashboard cards have JavaScript tests. A separate smoke-test suite runs against **real Home Assistant Core** with the remote Infuse endpoint mocked; it exercises config-entry setup/unload, offline availability, entity and resource registration, Reconfigure and discovery confirmation. End-to-end testing on actual tvOS devices and home networks is still necessary for reliable foreground/background and multicast behavior. See [Advanced setup](advanced.md) for commands.
