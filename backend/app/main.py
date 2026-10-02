import re
from datetime import date as Date
from typing import Literal
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Grateful Dead Archive API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

ARCHIVE_SEARCH_URL = "https://archive.org/advancedsearch.php"
ARCHIVE_METADATA_URL = "https://archive.org/metadata"
PAGE_SIZE = 100
ARCHIVE_SORTS = {
    "newest": "date desc",
    "oldest": "date asc",
    "rating": "avg_rating desc",
    "reviews": "num_reviews desc",
}
SEARCH_FIELDS = (
    "identifier",
    "title",
    "date",
    "year",
    "venue",
    "coverage",
    "description",
    "avg_rating",
    "num_reviews",
)


def group_recordings_by_show(records: list[dict], sort_by: str = "newest") -> list[dict]:
    shows: dict[tuple[str, str], dict] = {}
    for record in records:
        show_date = str(record.get("date", ""))[:10]
        place = record.get("venue") or record.get("coverage") or record.get("title", "")
        normalized_place = re.sub(r"[^a-z0-9]+", "", str(place).lower())
        key = (show_date, "" if show_date else normalized_place)
        current = shows.get(key)
        if current is None:
            shows[key] = {**record, "recording_count": 1}
            continue

        current["recording_count"] += 1
        if sort_by == "rating":
            current_rank = (
                float(current.get("avg_rating") or 0),
                int(current.get("num_reviews") or 0),
            )
            candidate_rank = (
                float(record.get("avg_rating") or 0),
                int(record.get("num_reviews") or 0),
            )
        else:
            current_rank = (
                int(current.get("num_reviews") or 0),
                float(current.get("avg_rating") or 0),
            )
            candidate_rank = (
                int(record.get("num_reviews") or 0),
                float(record.get("avg_rating") or 0),
            )
        if candidate_rank > current_rank:
            shows[key] = {**record, "recording_count": current["recording_count"]}

    return list(shows.values())


def normalize_setlist_text(value: object) -> str:
    if isinstance(value, (list, tuple)):
        value = " ".join(str(part) for part in value)
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


async def archive_get(url: str, params: list[tuple[str, str]] | None = None) -> dict:
    try:
        async with httpx.AsyncClient(
            timeout=25,
            headers={"User-Agent": "GratefulDeadArchiveExplorer/1.0"},
        ) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="The Internet Archive could not be reached. Please try again.",
        ) from exc


@app.get("/api/search")
async def search_shows(
    song: str | None = Query(default=None, max_length=120),
    venue: str | None = Query(default=None, max_length=120),
    show_date: Date | None = Query(default=None, alias="date"),
    min_rating: float = Query(default=0, ge=0, le=5),
    page: int = Query(default=1, ge=1),
    sort_by: Literal["newest", "oldest", "rating", "reviews"] = "newest",
) -> dict:
    query = ["collection:GratefulDead", "mediatype:etree"]
    if song and song.strip():
        phrase = song.strip().replace("\\", "\\\\").replace('"', '\\"')
        query.append(f'description:"{phrase}"')
    if venue and venue.strip():
        phrase = venue.strip().replace("\\", "\\\\").replace('"', '\\"')
        query.append(f'venue:"{phrase}"')
    if show_date:
        start = f"{show_date.isoformat()}T00:00:00Z"
        end = f"{show_date.isoformat()}T23:59:59Z"
        query.append(f"date:[{start} TO {end}]")
    if min_rating > 0:
        query.append(f"avg_rating:[{min_rating:g} TO 5]")

    params = [("q", " AND ".join(query))]
    params.extend(("fl[]", field) for field in SEARCH_FIELDS)
    params.extend(
        [
            ("rows", str(PAGE_SIZE)),
            ("page", str(page)),
            ("output", "json"),
            ("sort[]", ARCHIVE_SORTS[sort_by]),
        ]
    )
    payload = await archive_get(ARCHIVE_SEARCH_URL, params)
    response = payload.get("response", {})
    total = int(response.get("numFound", 0))
    records = response.get("docs", [])
    if page > 1:
        previous_params = [
            (key, str(page - 1) if key == "page" else value)
            for key, value in params
        ]
        previous_payload = await archive_get(ARCHIVE_SEARCH_URL, previous_params)
        previous_dates = {
            str(record.get("date", ""))[:10]
            for record in previous_payload.get("response", {}).get("docs", [])
            if record.get("date")
        }
        records = [
            record
            for record in records
            if str(record.get("date", ""))[:10] not in previous_dates
        ]

    if song and song.strip():
        normalized_song = normalize_setlist_text(song)
        records = [
            record
            for record in records
            if normalized_song in normalize_setlist_text(record.get("description"))
        ]
    if venue and venue.strip():
        normalized_venue = normalize_setlist_text(venue)
        records = [
            record
            for record in records
            if normalized_venue
            in normalize_setlist_text(
                " ".join(
                    str(record.get(field, ""))
                    for field in ("venue", "coverage", "title")
                )
            )
        ]

    results = group_recordings_by_show(records, sort_by)
    return {
        "total": total,
        "page": page,
        "pages": (total + PAGE_SIZE - 1) // PAGE_SIZE,
        "results": [
            {
                **record,
                "artwork": f"https://archive.org/services/img/{record['identifier']}",
            }
            for record in results
            if record.get("identifier")
        ],
    }


@app.get("/api/item/{identifier}")
async def get_show(identifier: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", identifier):
        raise HTTPException(status_code=400, detail="Invalid archive identifier.")

    payload = await archive_get(f"{ARCHIVE_METADATA_URL}/{identifier}")
    metadata = payload.get("metadata", {})
    if not metadata:
        raise HTTPException(status_code=404, detail="Show metadata was not found.")

    tracks_by_stem = {}
    format_priority = {".mp3": 0, ".ogg": 1, ".m4a": 2, ".wav": 3}
    for file in payload.get("files", []):
        name = file.get("name", "")
        extension = next((suffix for suffix in format_priority if name.lower().endswith(suffix)), None)
        if not extension:
            continue

        stem = name[:-len(extension)].lower()
        existing = tracks_by_stem.get(stem)
        if existing and existing["format_priority"] <= format_priority[extension]:
            continue

        track_match = re.search(r"-d(\d+)t(\d+)", name, re.IGNORECASE)
        metadata_track = re.search(r"\d+", str(file.get("track", "")))
        tracks_by_stem[stem] = {
            "name": name.rsplit("/", 1)[-1],
            "title": file.get("title") or "",
            "disc_number": int(track_match.group(1)) if track_match else 0,
            "track_number": int(metadata_track.group()) if metadata_track else (
                int(track_match.group(2)) if track_match else 0
            ),
            "url": f"https://archive.org/download/{identifier}/{quote(name, safe='')}",
            "format_priority": format_priority[extension],
        }

    tracks = sorted(
        tracks_by_stem.values(),
        key=lambda track: (track["disc_number"], track["track_number"], track["name"].lower()),
    )
    for track in tracks:
        del track["format_priority"]

    return {
        "identifier": identifier,
        "title": metadata.get("title", identifier),
        "description": metadata.get("description", ""),
        "notes": metadata.get("notes", ""),
        "venue": metadata.get("venue", ""),
        "coverage": metadata.get("coverage", ""),
        "artwork": f"https://archive.org/services/img/{identifier}",
        "tracks": tracks,
    }
