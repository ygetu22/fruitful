"""Sound search and genre planning checks; no provider requests."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from fruitful import sounds


class SoundSearchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        replacement = patch.dict(
            "os.environ",
            {
                "FREESOUND_API_TOKEN": "test-key-do-not-print",
                "FRUITFUL_LIBRARY_DB": str(Path(temporary.name) / "library.sqlite3"),
            },
        )
        replacement.start()
        self.addCleanup(replacement.stop)
        self.items = [
            {"id": i, "name": f"Kick {i}", "license": sounds.DEFAULT_LICENSE} for i in range(20)
        ]

    def response(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"results": self.items}
        ).encode()
        return response

    def test_short_search_does_not_truncate_later_cache_request(self):
        with patch.object(sounds, "urlopen", return_value=self.response()) as request:
            self.assertEqual(len(sounds.search_freesound("kick", 1)["results"]), 1)
            self.assertEqual(len(sounds.search_freesound("kick", 20)["results"]), 20)
        request.assert_called_once()
        sent = request.call_args.args[0]
        self.assertNotIn("test-key", sent.full_url)
        self.assertEqual(sent.get_header("Authorization"), "Token test-key-do-not-print")

    def test_filters_non_cc0_and_retains_source(self):
        self.items = [
            {
                "id": 1,
                "name": "CC0",
                "license": "https://creativecommons.org/publicdomain/zero/1.0/",
            },
            {"id": 2, "name": "Restricted", "license": "Attribution NonCommercial"},
        ]
        with patch.object(sounds, "urlopen", return_value=self.response()):
            result = sounds.search_freesound("kick")
        self.assertEqual([item["id"] for item in result["results"]], [1])

    def test_provider_errors_do_not_expose_key(self):
        failure = HTTPError(
            "https://example.invalid/?token=test-key-do-not-print", 401, "no", {}, None
        )
        with patch.object(sounds, "urlopen", side_effect=failure):
            with self.assertRaises(sounds.SoundSearchError) as caught:
                sounds.search_freesound("kick")
        self.assertIn("Check FREESOUND_API_TOKEN", str(caught.exception))
        self.assertNotIn("test-key", str(caught.exception))

    def test_unavailable_cache_does_not_break_search(self):
        with patch.object(sounds, "_connection", side_effect=OSError("read-only")):
            with patch.object(sounds, "urlopen", return_value=self.response()):
                self.assertEqual(len(sounds.search_freesound("kick")["results"]), 10)

    def test_malformed_preview_and_license_fields_do_not_crash_search(self):
        self.items = [
            {"id": 1, "name": "Kick", "license": sounds.DEFAULT_LICENSE, "previews": None},
            {"id": 2, "name": "Bad", "license": []},
            None,
        ]
        with patch.object(sounds, "urlopen", return_value=self.response()):
            result = sounds.search_freesound("kick")
        self.assertEqual(len(result["results"]), 1)
        self.assertIsNone(result["results"][0]["preview"])

    def test_corrupt_cache_is_ignored(self):
        with sounds._connection() as connection:
            connection.execute(
                "INSERT INTO sound_search_cache VALUES (?, ?, ?, ?)",
                ("search-v2:kick", sounds.DEFAULT_LICENSE, "[null]", sounds.time.time()),
            )
        with patch.object(sounds, "urlopen", return_value=self.response()) as request:
            self.assertEqual(sounds.search_freesound("kick")["source"], "freesound")
        request.assert_called_once()



class StyleTests(unittest.TestCase):
    def test_style_listing_cannot_mutate_saved_blueprints(self):
        from fruitful.styles import list_styles

        first = list_styles()
        first[0]["roles"].clear()
        self.assertTrue(list_styles()[0]["roles"])
