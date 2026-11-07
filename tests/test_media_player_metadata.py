"""Validate TV metadata against Home Assistant's media-player UI contract."""

from datetime import datetime, timezone
from enum import IntFlag, StrEnum
import importlib
import sys
from types import ModuleType, SimpleNamespace

from conftest import PACKAGE_NAME, model


def test_episode_metadata_is_displayed_as_tvshow(monkeypatch):
    """The frontend only renders the series subtitle for media type 'tvshow'."""
    ha = ModuleType("homeassistant")
    ha.__path__ = []
    components = ModuleType("homeassistant.components")
    components.__path__ = []
    media_player = ModuleType("homeassistant.components.media_player")
    config_entries = ModuleType("homeassistant.config_entries")
    core = ModuleType("homeassistant.core")
    util = ModuleType("homeassistant.util")
    util.__path__ = []
    dt = ModuleType("homeassistant.util.dt")

    class MediaType(StrEnum):
        EPISODE = "episode"
        TVSHOW = "tvshow"
        MOVIE = "movie"

    class MediaPlayerState(StrEnum):
        PLAYING = "playing"
        PAUSED = "paused"
        IDLE = "idle"

    class MediaPlayerEntityFeature(IntFlag):
        NONE = 0

    media_player.MediaPlayerEntity = type("MediaPlayerEntity", (), {})
    media_player.MediaPlayerEntityFeature = MediaPlayerEntityFeature
    media_player.MediaPlayerState = MediaPlayerState
    media_player.MediaType = MediaType
    config_entries.ConfigEntry = object
    core.HomeAssistant = object
    core.callback = lambda func: func
    dt.utcnow = lambda: datetime.now(timezone.utc)

    fake_entity = ModuleType(f"{PACKAGE_NAME}.entity")

    class InfuseEntity:
        def __init__(self, coordinator, entry, suffix):
            self.coordinator = coordinator

    fake_entity.InfuseEntity = InfuseEntity
    fake_coordinator = ModuleType(f"{PACKAGE_NAME}.coordinator")
    fake_coordinator.InfuseCoordinator = object

    for name, module in (
        ("homeassistant", ha),
        ("homeassistant.components", components),
        ("homeassistant.components.media_player", media_player),
        ("homeassistant.config_entries", config_entries),
        ("homeassistant.core", core),
        ("homeassistant.util", util),
        ("homeassistant.util.dt", dt),
        (f"{PACKAGE_NAME}.entity", fake_entity),
        (f"{PACKAGE_NAME}.coordinator", fake_coordinator),
    ):
        monkeypatch.setitem(sys.modules, name, module)

    name = f"{PACKAGE_NAME}.media_player"
    sys.modules.pop(name, None)
    try:
        mod = importlib.import_module(name)
        entry = SimpleNamespace(entry_id="test", title="Infuse", unique_id="test")
        episode = model.InfuseItem(kind="episode", title="Zurückgelassen", series_title="Reign", season=1, episode=7)
        snapshot = model.Playback(state="playing", position=110, duration=2400, item=episode,
                                  artwork_url="https://image.tmdb.org/t/p/w500/sample.jpg")
        coordinator = SimpleNamespace(data=snapshot)
        player = mod.InfuseMediaPlayer(coordinator, entry)
        assert player.media_content_type == MediaType.TVSHOW
        assert player.media_content_type.value == "tvshow"
        assert player.media_title == "Zurückgelassen"
        assert player.media_series_title == "Reign"
        assert player.media_season == "1"
        assert player.media_episode == "7"
        assert player.media_image_url == "https://image.tmdb.org/t/p/w500/sample.jpg"

        coordinator.data = model.Playback(
            state="playing", position=10, duration=100,
            item=model.InfuseItem(kind="movie", title="Example Movie"),
        )
        assert player.media_content_type == MediaType.MOVIE
        assert player.media_series_title is None
        assert player.media_image_url is None
    finally:
        sys.modules.pop(name, None)
