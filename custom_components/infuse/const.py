"""Constants for the Infuse Now Playing integration."""

DOMAIN = "infuse"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_NAME = "name"
CONF_DISCOVERY_NAME = "discovery_name"
CONF_POLL_INTERVAL = "poll_interval"
CONF_TMDB_TOKEN = "tmdb_token"
CONF_CLEAR_TMDB_TOKEN = "clear_tmdb_token"
CONF_LANGUAGE = "language"

DEFAULT_POLL_INTERVAL = 5
DEFAULT_LANGUAGE = "de-DE"

EVENT_STATE_CHANGED = "infuse_state_changed"
EVENT_MEDIA_CHANGED = "infuse_media_changed"
EVENT_PLAYBACK_STARTED = "infuse_playback_started"
EVENT_PLAYBACK_PAUSED = "infuse_playback_paused"
EVENT_PLAYBACK_RESUMED = "infuse_playback_resumed"
EVENT_PLAYBACK_IDLE = "infuse_playback_idle"
