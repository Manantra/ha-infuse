"""Test documented API fields and graceful optional metadata."""

import pytest
from conftest import model


def test_movie_snapshot():
    data = {
        "state": "playing", "positionSeconds": 420.5, "durationSeconds": 600,
        "item": {"kind": "movie", "tmdbID": "11", "imdbID": "tt0000011",
                 "tvdbID": None, "season": None, "episode": None,
                 "title": "Test Movie", "seriesTitle": None},
        "futureUnknownField": 123,
    }
    result = model.parse_now_playing(data)
    assert result.state == "playing"
    assert result.item.kind == "movie"
    assert result.item.tmdb_id == "11"
    assert result.progress == 70.1
    assert result.remaining_seconds == 179.5


def test_episode_snapshot():
    result = model.parse_now_playing({
        "state": "paused", "positionSeconds": 180, "durationSeconds": 2400,
        "item": {"kind": "episode", "title": "Pilot", "seriesTitle": "Example",
                 "tmdbID": "22", "season": 0, "episode": 1},
    })
    assert result.item.season == 0
    assert result.item.episode == 1
    assert result.item.series_title == "Example"


def test_idle_discards_stale_metadata():
    result = model.parse_now_playing({
        "state": "idle", "positionSeconds": 777, "durationSeconds": 1000,
        "item": {"kind": "movie", "title": "stale"},
    })
    assert result.item is None
    assert result.position is None
    assert result.progress is None


@pytest.mark.parametrize("invalid", [
    [], None, {"state": "buffering"}, {"state": True},
    {"state": "playing", "positionSeconds": -1},
    {"state": "playing", "positionSeconds": float("nan")},
    {"state": "playing", "durationSeconds": True},
    {"state": "playing", "item": ["bad"]},
    {"state": "playing", "item": {"kind": "song"}},
    {"state": "playing", "item": {"kind": "episode", "season": "2"}},
])
def test_invalid_responses(invalid):
    with pytest.raises(model.InfuseInvalidResponse):
        model.parse_now_playing(invalid)


def test_progress_clamped_and_zero_duration():
    p = model.Playback("playing", 200, 100, None)
    assert p.progress == 100
    assert p.remaining_seconds == 0
    assert model.Playback("paused", 0, 0, None).progress is None


def test_item_identity_changes_across_episode():
    a = model.InfuseItem(kind="episode", tmdb_id="123", season=1, episode=1)
    b = model.InfuseItem(kind="episode", tmdb_id="123", season=1, episode=2)
    assert a.identity != b.identity
