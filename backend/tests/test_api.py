from fastapi.testclient import TestClient

import app.main as api


client = TestClient(api.app)


def test_search_scopes_collection_and_applies_filters(monkeypatch):
    captured = {}

    async def fake_archive_get(url, params=None):
        captured["url"] = url
        captured["params"] = dict(params)
        return {
            "response": {
                "numFound": 1,
                "docs": [
                    {
                        "identifier": "gd-test-1977-05-08-low-review",
                        "title": "Grateful Dead Live at Barton Hall",
                        "date": "1977-05-08T00:00:00Z",
                        "venue": "Barton Hall",
                        "description": "Scarlet Begonias, Fire on the Mountain",
                        "avg_rating": 5.0,
                        "num_reviews": 2,
                    },
                    {
                        "identifier": "gd-test-1977-05-08",
                        "title": "Grateful Dead Live at Barton Hall",
                        "date": "1977-05-08T00:00:00Z",
                        "venue": "Barton Hall, Cornell University",
                        "description": "Scarlet Begonias, Fire on the Mountain",
                        "avg_rating": 4.8,
                        "num_reviews": 12,
                    },
                    {
                        "identifier": "gd-test-1977-05-09",
                        "title": "Grateful Dead Live at Barton Hall",
                        "date": "1977-05-09T00:00:00Z",
                        "venue": "Barton Hall",
                        "description": "Scarlet Begonias",
                        "avg_rating": 4.7,
                        "num_reviews": 8,
                    },
                ],
            }
        }

    monkeypatch.setattr(api, "archive_get", fake_archive_get)
    response = client.get(
        "/api/search",
        params={"song": "Scarlet Begonias", "date": "1977-05-08", "min_rating": 4},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["identifier"] == "gd-test-1977-05-08"
    assert results[0]["recording_count"] == 2
    assert results[0]["artwork"].endswith("gd-test-1977-05-08")
    query = captured["params"]["q"]
    assert "collection:GratefulDead" in query
    assert "mediatype:etree" in query
    assert 'description:"Scarlet Begonias"' in query
    assert "1977-05-08T00:00:00Z" in query
    assert "avg_rating:[4 TO 5]" in query


def test_venue_search_and_sort_are_sent_to_archive(monkeypatch):
    captured = {}

    async def fake_archive_get(url, params=None):
        captured["params"] = dict(params)
        return {"response": {"numFound": 0, "docs": []}}

    monkeypatch.setattr(api, "archive_get", fake_archive_get)
    response = client.get(
        "/api/search",
        params={"venue": "Barton Hall", "sort_by": "rating"},
    )

    assert response.status_code == 200
    assert 'venue:"Barton Hall"' in captured["params"]["q"]
    assert captured["params"]["sort[]"] == "avg_rating desc"


def test_venue_search_filters_metadata_aliases(monkeypatch):
    async def fake_archive_get(url, params=None):
        return {
            "response": {
                "numFound": 2,
                "docs": [
                    {
                        "identifier": "gd-barton",
                        "date": "1977-05-08T00:00:00Z",
                        "venue": "Barton Hall, Cornell University",
                    },
                    {
                        "identifier": "gd-other",
                        "date": "1977-05-09T00:00:00Z",
                        "venue": "Other Hall",
                    },
                ],
            }
        }

    monkeypatch.setattr(api, "archive_get", fake_archive_get)
    response = client.get("/api/search", params={"venue": "Barton Hall"})

    assert response.status_code == 200
    assert [show["identifier"] for show in response.json()["results"]] == ["gd-barton"]


def test_item_returns_playable_files_and_skips_lossless_source(monkeypatch):
    async def fake_archive_get(url, params=None):
        return {
            "metadata": {"title": "Grateful Dead Live", "description": "Setlist"},
            "files": [
                {"name": "gd-test-d1t01.mp3", "title": "Morning Dew", "track": "1"},
                {"name": "gd-test-d1t01.ogg"},
                {"name": "gd-test-d1t02.ogg"},
                {"name": "gd-test-d1t03.shn"},
            ],
        }

    monkeypatch.setattr(api, "archive_get", fake_archive_get)
    response = client.get("/api/item/gd-test-1977-05-08")

    assert response.status_code == 200
    tracks = response.json()["tracks"]
    assert [track["name"] for track in tracks] == ["gd-test-d1t01.mp3", "gd-test-d1t02.ogg"]
    assert tracks[0]["title"] == "Morning Dew"
    assert tracks[0]["track_number"] == 1
    assert tracks[0]["url"].startswith("https://archive.org/download/gd-test-1977-05-08/")


def test_search_skips_same_show_from_previous_page(monkeypatch):
    async def fake_archive_get(url, params=None):
        page = dict(params)["page"]
        docs = (
            [
                {"identifier": "gd-test-1977-05-08", "date": "1977-05-08T00:00:00Z"},
                {"identifier": "gd-test-1977-05-09", "date": "1977-05-09T00:00:00Z"},
            ]
            if page == "1"
            else [
                {"identifier": "gd-test-1977-05-09-copy", "date": "1977-05-09T00:00:00Z"},
                {"identifier": "gd-test-1977-05-10", "date": "1977-05-10T00:00:00Z"},
            ]
        )
        return {"response": {"numFound": 200, "docs": docs}}

    monkeypatch.setattr(api, "archive_get", fake_archive_get)
    response = client.get("/api/search", params={"page": 2})

    assert response.status_code == 200
    assert [show["identifier"] for show in response.json()["results"]] == ["gd-test-1977-05-10"]


def test_song_search_excludes_results_without_song_in_displayed_setlist(monkeypatch):
    async def fake_archive_get(url, params=None):
        return {
            "response": {
                "numFound": 2,
                "docs": [
                    {
                        "identifier": "gd1995-07-09",
                        "title": "Grateful Dead Live at Soldier Field on 1995-07-09",
                        "date": "1995-07-09T00:00:00Z",
                        "description": "Touch Of Grey, Black Muddy River, Box Of Rain",
                    },
                    {
                        "identifier": "gd1995-07-08",
                        "title": "Grateful Dead Live at Soldier Field on 1995-07-08",
                        "date": "1995-07-08T00:00:00Z",
                        "description": "Jack Straw, Sugaree, Althea",
                    },
                ],
            }
        }

    monkeypatch.setattr(api, "archive_get", fake_archive_get)
    response = client.get("/api/search", params={"song": "Sugaree"})

    assert response.status_code == 200
    assert [show["identifier"] for show in response.json()["results"]] == ["gd1995-07-08"]