"""Firecore deep-link coverage."""

from urllib.parse import parse_qsl, urlsplit
import pytest
from conftest import links


def test_library_links_all_supported_kinds():
    assert links.library_link("movie", 1327819, autoplay=True) == "infuse://movie/1327819?play"
    assert links.library_link("series", "42") == "infuse://series/42"
    assert links.library_link("season", 42, season=0) == "infuse://series/42-0"
    assert links.library_link("episode", 42, season=3, episode=5, autoplay=True) == "infuse://series/42-3-5?play"


@pytest.mark.parametrize("kind,mid,season,episode", [
    ("movie", 0, None, None), ("song", 22, None, None),
    ("episode", 11, None, 1), ("episode", 11, 1, None),
    ("episode", 11, 1, 0), ("season", 5, -1, None),
    ("movie", "abc", None, None),
])
def test_invalid_library_links(kind, mid, season, episode):
    with pytest.raises(ValueError):
        links.library_link(kind, mid, season=season, episode=episode)


def test_stream_playlist_order_and_percent_encoding():
    result = links.stream_link("play", [
        {"url": "https://example.test/video?token=a&v=1", "position": 30,
         "filename": "Film S01 E01.mkv", "subtitle": "https://example.test/untertitel.srt"},
        {"url": "http://192.168.1.10/2.mp4", "position": 0},
    ], x_success="myapp://success", x_error="myapp://error")
    fields = parse_qsl(urlsplit(result).query)
    assert fields == [
        ("url", "https://example.test/video?token=a&v=1"),
        ("position", "30"), ("filename", "Film S01 E01.mkv"),
        ("sub", "https://example.test/untertitel.srt"),
        ("url", "http://192.168.1.10/2.mp4"), ("position", "0"),
        ("x-success", "myapp://success"), ("x-error", "myapp://error"),
    ]


def test_save_and_download():
    result = links.stream_link("save", [{"url": "https://example.test/file.mkv"}], download=True)
    assert ("download", "1") in parse_qsl(urlsplit(result).query)


@pytest.mark.parametrize("action,streams,download", [
    ("play", [], False), ("play", [{"url": "data:text/html,hi"}], False),
    ("play", [{"url": "javascript:alert(1)"}], False),
    ("play", [{"url": "https://x", "position": -1}], False),
    ("save", [{"url": "https://x", "position": 1}], False),
    ("play", [{"url": "https://x"}], True),
])
def test_reject_bad_streams(action, streams, download):
    with pytest.raises(ValueError):
        links.stream_link(action, streams, download=download)
