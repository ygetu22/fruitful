"""Piano Roll request cleanup with a fake trigger."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fruitful.pianoroll import PianoRollBridge, PianoRollError


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
