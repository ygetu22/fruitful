"""Run the FL script against fake API modules to check validation before writes."""

import runpy
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class DeviceValidationTests(unittest.TestCase):
    def setUp(self):
        self.modules = {
            name: MagicMock()
            for name in ("channels", "device", "general", "mixer", "plugins", "transport")
        }
        self.modules["channels"].channelCount.return_value = 3
        self.modules["mixer"].getTrackCount.return_value = 10
        self.modules["plugins"].isValid.return_value = True
        self.modules["plugins"].getParamCount.return_value = 4
        with patch.dict("sys.modules", self.modules):
            script = Path(__file__).resolve().parents[1] / "device/device_Fruitful.py"
            self.dispatch = runpy.run_path(str(script))["_dispatch"]

    def test_invalid_channel_cannot_target_selected_channel(self):
        with self.assertRaises(ValueError):
            self.dispatch("set_channel_volume", {"channel": -1, "value": 0.5})
        self.modules["channels"].setChannelVolume.assert_not_called()

    def test_entire_pattern_is_checked_before_first_write(self):
        with self.assertRaises(ValueError):
            self.dispatch("program_pattern", {"channel": 0, "steps": [True, "invalid"]})
        self.modules["channels"].setGridBit.assert_not_called()

    def test_invalid_mixer_route_is_rejected(self):
        with self.assertRaises(ValueError):
            self.dispatch("route_channel_to_mixer", {"channel": 0, "track": 10})
        self.modules["channels"].setTargetFxTrack.assert_not_called()

    def test_invalid_plugin_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            self.dispatch("set_plugin_param", {"index": 0, "param": 4, "value": 0.5})
        self.modules["plugins"].setParamValue.assert_not_called()

    def test_nonfinite_tempo_is_rejected(self):
        with self.assertRaises(ValueError):
            self.dispatch("set_tempo", {"bpm": float("nan")})
        self.modules["mixer"].setCurrentTempo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
