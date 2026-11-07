"""Keep cover enrichment opt-in and scoped to the correct TMDB media type."""

import pytest
from conftest import metadata, model


class FakeResponse:
    status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def raise_for_status(self):
        return None

    async def json(self):
        return {"poster_path": "/reign-series-poster.jpg"}


class FakeSession:
    def __init__(self):
        self.requests = []

    def get(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return FakeResponse()


@pytest.mark.asyncio
async def test_episode_cover_requests_tv_poster_with_read_token():
    session = FakeSession()
    item = model.InfuseItem(kind="episode", tmdb_id="48865", title="Zurückgelassen", series_title="Reign")
    url = await metadata.fetch_tmdb_artwork(session, "test-read-access-token", item, "de-DE")
    assert url == "https://image.tmdb.org/t/p/w500/reign-series-poster.jpg"
    endpoint, kwargs = session.requests[0]
    assert endpoint == "https://api.themoviedb.org/3/tv/48865"
    assert kwargs["headers"]["Authorization"] == "Bearer test-read-access-token"
    assert kwargs["params"]["language"] == "de-DE"


@pytest.mark.asyncio
async def test_missing_tmdb_id_does_not_make_external_request():
    session = FakeSession()
    item = model.InfuseItem(kind="episode", title="Pilot")
    assert await metadata.fetch_tmdb_artwork(session, "token", item, "de-DE") is None
    assert not session.requests
