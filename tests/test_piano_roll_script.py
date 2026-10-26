"""Exercise the generated Piano Roll script with an in-memory score."""

import json
import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fruitful.pianoroll import PianoRollBridge, PianoRollError
from fruitful.setup import install_scripts


class Score:
    PPQ = 96

    def __init__(self):
        self.notes = []

    @property
    def noteCount(self):
        return len(self.notes)

    def getNote(self, index):
        return self.notes[index]

    def addNote(self, note):
        self.notes.append(note)

    def deleteNote(self, index):
        del self.notes[index]


class PianoRollScriptTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        settings = Path(temporary.name) / "Settings"
        settings.mkdir()
        with patch("builtins.print"):
            install_scripts(settings, piano_roll=True, dry_run=False, force=False)
        self.directory = settings / "Piano roll scripts"
        self.score = Score()
        api = SimpleNamespace(score=self.score, Note=SimpleNamespace)
        with patch.dict("sys.modules", {"flpianoroll": api}):
            self.apply = runpy.run_path(str(self.directory / "Fruitful Apply.pyscript"))["apply"]

    def request(self, action, notes):
        (self.directory / "fruitful_request.json").write_text(
            json.dumps(
                {
                    "id": "test-request",
                    "action": action,
                    "args": {"notes": notes},
                }
            )
        )
        self.apply()
        return json.loads((self.directory / "fruitful_response.json").read_text())

    def test_shortcut_cannot_replay_note_write(self):
        result = self.request("add_notes", [{"number": 60, "time": 0, "length": 1}])
        self.assertTrue(result["ok"])
        self.assertFalse((self.directory / "fruitful_request.json").exists())
        self.apply()
        self.assertEqual(len(self.score.notes), 1)

    def test_invalid_replacement_preserves_existing_notes(self):
        original = SimpleNamespace(number=72, time=0, length=96, velocity=0.8)
        self.score.notes.append(original)
        result = self.request(
            "replace_notes",
            [
                {"number": 60, "time": 0, "length": 1},
                {"number": 200, "time": 1, "length": 1},
            ],
        )
        self.assertFalse(result["ok"])
        self.assertEqual(self.score.notes, [original])

    def test_empty_replacement_cannot_clear_notes(self):
        self.score.notes.append(SimpleNamespace(number=72, time=0, length=96, velocity=0.8))
        result = self.request("replace_notes", [])
        self.assertFalse(result["ok"])
        self.assertEqual(len(self.score.notes), 1)

    def test_positive_length_is_at_least_one_tick(self):
        result = self.request("add_notes", [{"number": 60, "time": 0, "length": 0.001}])
        self.assertTrue(result["ok"])
        self.assertEqual(self.score.notes[0].length, 1)


class PianoRollBridgeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        replacement = patch.dict("os.environ", {"FRUITFUL_PIANO_ROLL_DIR": temporary.name})
        replacement.start()
        self.addCleanup(replacement.stop)
        self.bridge = PianoRollBridge(timeout=0.01)

    def test_failed_trigger_cannot_leave_a_pending_write(self):
        with patch.object(self.bridge, "_trigger", side_effect=PianoRollError("Permission denied")):
            with self.assertRaises(PianoRollError):
                self.bridge.call("add_notes", notes=[])
        self.assertFalse((self.directory / "fruitful_request.json").exists())
        self.assertFalse((self.directory / "fruitful_request.tmp").exists())

    def test_malformed_response_times_out_without_pending_request(self):
        (self.directory / "fruitful_response.json").write_text("[]")
        with patch.object(self.bridge, "_trigger"):
            with self.assertRaisesRegex(PianoRollError, "Changes may have applied"):
                self.bridge.call("get_notes")
        self.assertFalse((self.directory / "fruitful_request.json").exists())

    def test_matching_response_returns_notes(self):
        def respond():
            request = json.loads((self.directory / "fruitful_request.json").read_text())
            (self.directory / "fruitful_response.json").write_text(
                json.dumps(
                    {
                        "id": request["id"],
                        "ok": True,
                        "result": [{"number": 60}],
                    }
                )
            )

        with patch.object(self.bridge, "_trigger", side_effect=respond):
            self.assertEqual(self.bridge.call("get_notes"), [{"number": 60}])
        self.assertFalse((self.directory / "fruitful_request.json").exists())
