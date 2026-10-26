"""Failure handling with fake MIDI and FL responses; no real FL commands."""

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import mido

from fruitful import protocol, server, sounds
from fruitful.bridge import Bridge, BridgeError, BridgeTimeout, _find_port


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = Bridge(timeout=0.01)
        self.output = MagicMock()
        self.input = MagicMock()
        for name, result in [
            ("get_input_names", ["Fruitful Request"]),
            ("get_output_names", ["Fruitful Request"]),
            ("open_input", self.input),
            ("open_output", self.output),
        ]:
            replacement = patch("fruitful.bridge.mido." + name, return_value=result)
            replacement.start()
            self.addCleanup(replacement.stop)
        self.addCleanup(self.bridge.close)

    def respond(self, message):
        _, request = protocol.decode(list(message.data))
        response = mido.Message(
            "sysex",
            data=protocol.encode(
                protocol.DIR_RESPONSE,
                {
                    "id": request["id"],
                    "ok": True,
                    "result": {"pong": True},
                },
            ),
        )
        self.bridge._on_message(response)
        self.bridge._on_message(response)  # Duplicate delivery must never block.

    def test_duplicate_replies_do_not_block(self):
        self.output.send.side_effect = self.respond
        self.assertEqual(self.bridge.call("ping"), {"pong": True})
        self.assertEqual(self.bridge._pending, {})

    def test_separate_bridges_start_with_distinct_request_ids(self):
        with patch("fruitful.bridge.secrets.randbits", side_effect=[10, 20]):
            first = Bridge()
            second = Bridge()
        self.assertEqual(next(first._ids), 11)
        self.assertEqual(next(first._ids), 12)
        self.assertEqual(next(second._ids), 21)

    def test_send_failure_cleans_pending_and_closes_connection(self):
        self.output.send.side_effect = OSError("disconnected")
        with self.assertRaisesRegex(BridgeError, "may have applied"):
            self.bridge.call("ping")
        self.assertEqual(self.bridge._pending, {})
        self.assertIsNone(self.bridge._out)
        self.output.send.assert_called_once()
        self.output.close.assert_called_once()
        self.input.close.assert_called_once()

    def test_timeout_is_not_retried_and_next_call_reopens(self):
        with self.assertRaisesRegex(BridgeTimeout, "may have been applied"):
            self.bridge.call("ping")
        self.assertEqual(self.bridge._pending, {})
        self.assertIsNone(self.bridge._out)
        self.output.send.assert_called_once()
        self.output.send.side_effect = self.respond
        self.assertEqual(self.bridge.call("ping"), {"pong": True})

    def test_input_open_failure_closes_output(self):
        with patch("fruitful.bridge.mido.open_input", side_effect=OSError("unplugged")):
            with self.assertRaises(BridgeError):
                self.bridge.call("ping")
        self.output.close.assert_called_once()
        self.assertEqual(self.bridge._pending, {})

    def test_malformed_responses_are_ignored(self):
        for payload in [[], {"id": []}, {"id": True}, {"id": 100}]:
            self.bridge._on_message(
                mido.Message("sysex", data=protocol.encode(protocol.DIR_RESPONSE, payload))
            )
        self.assertEqual(self.bridge._pending, {})

    def test_parallel_requests_complete(self):
        self.output.send.side_effect = self.respond
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: self.bridge.call("ping"), range(12)))
        self.assertEqual(results, [{"pong": True}] * 12)
        self.assertEqual(self.bridge._pending, {})

    def test_bad_values_never_open_midi(self):
        for command, arguments in [
            ("set_step", {"channel": -1}),
            ("set_grid_bit", {"step": 64}),
            ("set_tempo", {"bpm": float("nan")}),
            ("set_channel_volume", {"value": 2}),
            ("program_pattern", {"steps": []}),
            ("program_pattern", {"steps": ["yes"]}),
            ("program_pattern", {"steps": [True] * 65}),
        ]:
            with self.subTest(command=command, arguments=arguments), self.assertRaises(ValueError):
                self.bridge.call(command, **arguments)
        self.output.send.assert_not_called()

    def test_ambiguous_ports_fail_and_exact_match_wins(self):
        with self.assertRaisesRegex(BridgeError, "More than one"):
            _find_port("Fruitful Request", ["Bus Fruitful Request A", "Bus Fruitful Request B"])
        self.assertEqual(
            _find_port("Fruitful Request", ["Bus Fruitful Request", "Fruitful Request"]),
            "Fruitful Request",
        )


class StarterTests(unittest.TestCase):
    def setUp(self):
        self.rows = {}
        self.channels = [
            {"name": name, "index": i} for i, name in enumerate(["Kick", "Clap", "Closed Hat"])
        ]
        replacement = patch.object(server, "_bridge")
        self.bridge = replacement.start()
        self.addCleanup(replacement.stop)
        self.bridge.call.side_effect = self.call

    def call(self, command, **arguments):
        if command == "get_project_state":
            return {"channels": self.channels}
        if command == "program_pattern":
            self.rows[arguments["channel"]] = arguments["steps"]
        if command == "get_pattern":
            return self.rows[arguments["channel"]]
        if command == "set_tempo":
            return arguments["bpm"]

    def test_success_requires_readback(self):
        result = server.start_house_beat(play=False)
        self.assertTrue(result["drums_verified"])
        self.assertFalse(result["playing"])
        self.assertEqual(len(self.rows), 3)
        self.assertEqual(
            sum(c.args == ("get_pattern",) for c in self.bridge.call.call_args_list), 3
        )
        self.assertFalse(any(c.args == ("transport",) for c in self.bridge.call.call_args_list))

    def test_mismatch_stops_before_playback(self):
        original = self.call
        self.bridge.call.side_effect = lambda cmd, **args: (
            [False] * 16 if cmd == "get_pattern" else original(cmd, **args)
        )
        with self.assertRaisesRegex(BridgeError, "Could not check Kick"):
            server.start_house_beat()
        self.assertFalse(any(c.args == ("transport",) for c in self.bridge.call.call_args_list))

    def test_partial_failure_names_confirmed_changes(self):
        original = self.call

        def fail_second(command, **arguments):
            if command == "program_pattern" and arguments["channel"] == 1:
                raise BridgeTimeout("No reply")
            return original(command, **arguments)

        self.bridge.call.side_effect = fail_second
        with self.assertRaisesRegex(BridgeError, "Confirmed drum rows: Kick"):
            server.start_house_beat()

    def test_missing_role_causes_no_writes(self):
        self.channels.pop()
        with self.assertRaises(ValueError):
            server.start_house_beat()
        self.assertEqual(self.rows, {})

    def test_open_hat_and_partial_word_are_not_selected(self):
        for name in ["Open HiHat", "Open_HiHat", "Open-HiHat", "Kickstart"]:
            channels = [
                {"index": 0, "name": name},
                {"index": 1, "name": "Clap"},
                {"index": 2, "name": "Kick"},
            ]
            with self.assertRaises(ValueError):
                server._house_channel_indexes(channels)

    def test_nonfinite_and_empty_note_writes_fail(self):
        for notes in [
            [],
            [{"number": 60.5, "time": 0, "length": 1}],
            [{"number": 60, "time": float("nan"), "length": 1}],
            [{"number": 60, "time": 0, "length": float("inf")}],
        ]:
            with self.assertRaises(ValueError):
                server._validated_notes(notes)


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


if __name__ == "__main__":
    unittest.main()
