# Contributing

Thanks for helping build Infuse Now Playing for Home Assistant.

- Keep the Firecore HTTP API read-only; do not advertise unsupported playback controls.
- Every Infuse instance must have separate playback state, coordinator, entities and events.
- Never infer an Apple TV user profile from the current media title or presence.
- Keep core functionality local and independent from TMDB and custom dashboard cards.
- Update relevant tests and documentation with changes in behavior.
- Avoid including IP addresses, private stream URLs, credentials, account data or sensitive logs in issues.

To contribute, create a feature branch, run the tests, and open a pull request describing the behavior and test coverage.
