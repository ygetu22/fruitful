"""Opt-in Freesound search with a local metadata cache and strict license filtering."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FREESOUND_SEARCH_URL = "https://freesound.org/apiv2/search/"
DEFAULT_LICENSE = "Creative Commons 0"
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


class SoundSearchError(RuntimeError):
    """A licensed sound search could not be completed."""


def _database_path() -> Path:
    configured = os.environ.get("FRUITFUL_LIBRARY_DB")
    return (
        Path(configured).expanduser()
        if configured
        else Path.home() / ".fruitful" / "library.sqlite3"
    )


@contextmanager
def _connection():
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        with connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS sound_search_cache (
                query TEXT NOT NULL, license TEXT NOT NULL, results TEXT NOT NULL, fetched_at REAL NOT NULL,
                PRIMARY KEY (query, license))"""
            )
            yield connection
    finally:
        connection.close()


def _cached_results(query: str, license_name: str) -> list[dict] | None:
    with _connection() as connection:
        row = connection.execute(
            "SELECT results, fetched_at FROM sound_search_cache WHERE query = ? AND license = ?",
            (query, license_name),
        ).fetchone()
    if row is None or time.time() - row[1] > CACHE_TTL_SECONDS:
        return None
    results = json.loads(row[0])
    if not isinstance(results, list) or any(not isinstance(item, dict) for item in results):
        return None
    return results


def _cache_results(query: str, license_name: str, results: list[dict]) -> None:
    with _connection() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO sound_search_cache (query, license, results, fetched_at) VALUES (?, ?, ?, ?)",
            (query, license_name, json.dumps(results), time.time()),
        )


def search_freesound(query: str, limit: int = 10) -> dict:
    """Search CC0 sounds and persist only metadata locally for a week."""
    normalized = " ".join(query.split())
    if not normalized:
        raise ValueError("sound search query must not be empty")
    if not 1 <= limit <= 20:
        raise ValueError("sound search limit must be between 1 and 20")

    cache_key = "search-v2:" + normalized
    try:
        cached = _cached_results(cache_key, DEFAULT_LICENSE)
    except (OSError, sqlite3.Error, ValueError):
        cached = None
    if cached is not None:
        return {"source": "cache", "license": DEFAULT_LICENSE, "results": cached[:limit]}

    token = os.environ.get("FREESOUND_API_TOKEN")
    if not token:
        raise SoundSearchError(
            "FREESOUND_API_TOKEN is not configured. Create a free Freesound API key, then set it in the MCP server environment."
        )
    parameters = urlencode(
        {
            "query": normalized,
            "filter": f'license:"{DEFAULT_LICENSE}"',
            "fields": "id,name,tags,license,previews,duration,type",
            "page_size": 20,
        }
    )
    request = Request(
        f"{FREESOUND_SEARCH_URL}?{parameters}",
        headers={"User-Agent": "Fruitful/0.1", "Authorization": f"Token {token}"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise SoundSearchError(
                    "Freesound returned too much data. Try a more specific search."
                )
            payload = json.loads(data)
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise ValueError("Missing search results")
    except HTTPError as error:
        if error.code in {401, 403}:
            message = (
                "Freesound rejected the API key. Check FREESOUND_API_TOKEN in your MCP client."
            )
        elif error.code == 429:
            message = "Freesound's request limit was reached. Try again later."
        else:
            message = "Freesound is unavailable. Try again later."
        raise SoundSearchError(message) from None
    except (URLError, OSError, TimeoutError):
        raise SoundSearchError(
            "Could not reach Freesound. Check your connection and try again."
        ) from None
    except (ValueError, UnicodeError):
        raise SoundSearchError(
            "Freesound returned an unreadable response. Try again later."
        ) from None
    results = []
    allowed_licenses = {
        DEFAULT_LICENSE,
        "https://creativecommons.org/publicdomain/zero/1.0/",
        "http://creativecommons.org/publicdomain/zero/1.0/",
    }
    for item in payload["results"]:
        if not isinstance(item, dict):
            continue
        if type(item.get("id")) is not int or not isinstance(item.get("name"), str):
            continue
        license_name = item.get("license")
        if not isinstance(license_name, str) or license_name not in allowed_licenses:
            continue
        previews = item.get("previews")
        results.append(
            {
                "id": item["id"],
                "name": item["name"],
                "tags": item.get("tags", []),
                "license": item.get("license"),
                "duration": item.get("duration"),
                "preview": previews.get("preview-hq-mp3") if isinstance(previews, dict) else None,
            }
        )
    try:
        _cache_results(cache_key, DEFAULT_LICENSE, results)
    except (OSError, sqlite3.Error):
        pass  # Search results remain usable when the optional local cache is unavailable.
    return {"source": "freesound", "license": DEFAULT_LICENSE, "results": results[:limit]}
