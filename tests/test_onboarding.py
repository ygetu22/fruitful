"""Onboarding regression checks; all file writes stay in temporary folders."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from fruitful.cli import doctor
from fruitful.setup import install_scripts, installation_files, settings_directory


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fruitful setup ያ ")
        self.addCleanup(self.temporary.cleanup)
        self.settings = Path(self.temporary.name) / "FL Studio/Settings"
        self.settings.mkdir(parents=True)
        self.output = io.StringIO()
        capture = redirect_stdout(self.output)
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)

    def test_requires_existing_settings_folder(self):
        self.assertEqual(settings_directory(str(self.settings)), self.settings.resolve())
        for path in [self.settings.parent, self.settings / "missing"]:
            with self.assertRaises(ValueError):
                settings_directory(str(path))

    def test_preview_makes_no_files(self):
        install_scripts(self.settings, piano_roll=True, dry_run=True, force=False)
        self.assertEqual(list(self.settings.iterdir()), [])
        self.assertIn("Preview only", self.output.getvalue())

    def test_install_generates_portable_piano_roll_script(self):
        install_scripts(self.settings, piano_roll=True, dry_run=False, force=False)
        for path, content in installation_files(self.settings, True).items():
            self.assertEqual(path.read_text(), content)
            compile(content, str(path), "exec")
        piano = self.settings / "Piano roll scripts/Fruitful Apply.pyscript"
        self.assertIn(repr(str(piano.parent)), piano.read_text())
        self.assertNotIn('"__FRUITFUL_PIANO_ROLL_DIR__"', piano.read_text())
        self.assertNotIn("/Volumes/LaCie", piano.read_text())

    def test_repeat_install_preserves_files(self):
        install_scripts(self.settings, True, False, False)
        before = {p: p.stat().st_mtime_ns for p in installation_files(self.settings, True)}
        install_scripts(self.settings, True, False, False)
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in before})

    def test_conflict_preflight_prevents_partial_install(self):
        piano = self.settings / "Piano roll scripts/Fruitful Apply.pyscript"
        piano.parent.mkdir()
        piano.write_text("# personal changes\n")
        with self.assertRaises(ValueError):
            install_scripts(self.settings, True, False, False)
        self.assertFalse((self.settings / "Hardware").exists())
        self.assertEqual(piano.read_text(), "# personal changes\n")
        install_scripts(self.settings, True, False, True)
        self.assertEqual(piano.read_text(), installation_files(self.settings, True)[piano])

    def test_refuses_symlink_even_with_force(self):
        target = self.settings / "elsewhere.py"
        target.write_text("# keep\n")
        path = self.settings / "Hardware/Fruitful/device_Fruitful.py"
        path.parent.mkdir(parents=True)
        path.symlink_to(target)
        with self.assertRaises(ValueError):
            install_scripts(self.settings, False, False, True)
        self.assertEqual(target.read_text(), "# keep\n")


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.output = io.StringIO()
        capture = redirect_stdout(self.output)
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)
        for name, value in [
            ("fruitful.cli.sys.platform", "darwin"),
            ("mido.get_input_names", None),
            ("mido.get_output_names", None),
            ("fruitful.bridge.Bridge", None),
        ]:
            replacement = patch(name, value) if value is not None else patch(name)
            mocked = replacement.start()
            self.addCleanup(replacement.stop)
            if name.endswith("get_input_names"):
                self.inputs = mocked
                mocked.return_value = ["IAC Driver Fruitful Request"]
            elif name.endswith("get_output_names"):
                mocked.return_value = ["IAC Driver Fruitful Request"]
            elif name.endswith("Bridge"):
                self.bridge = mocked
                mocked.return_value.call.return_value = {"pong": True, "fl_version": "test-version"}

    def test_offline_never_contacts_fl(self):
        self.assertEqual(doctor(None, offline=True, piano_roll=False), 0)
        self.bridge.assert_not_called()
        self.assertIn("SKIP: FL connection", self.output.getvalue())

    def test_missing_iac_is_actionable(self):
        self.inputs.return_value = []
        self.assertEqual(doctor(None, False, False), 1)
        self.bridge.assert_not_called()
        self.assertIn("Enable the IAC Driver", self.output.getvalue())

    def test_unavailable_midi_backend_is_actionable(self):
        self.inputs.side_effect = RuntimeError("backend unavailable")
        self.assertEqual(doctor(None, False, False), 1)
        self.assertIn("reinstall Fruitful", self.output.getvalue())

    def test_connected_ping_closes_ports(self):
        self.assertEqual(doctor(None, False, False), 0)
        self.bridge.return_value.call.assert_called_once_with("ping")
        self.bridge.return_value.close.assert_called_once()

    def test_disconnected_fl_closes_ports_and_reports_fix(self):
        from fruitful.bridge import BridgeTimeout

        self.bridge.return_value.call.side_effect = BridgeTimeout("No response")
        self.assertEqual(doctor(None, False, False), 1)
        self.bridge.return_value.close.assert_called_once()
        self.assertIn("same FL port number", self.output.getvalue())

    def test_unexpected_reply_fails(self):
        self.bridge.return_value.call.return_value = {"pong": False}
        self.assertEqual(doctor(None, False, False), 1)
        self.assertIn("Unexpected ping reply", self.output.getvalue())

    def test_missing_scripts_fail_even_when_midi_is_present(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(doctor(Path(temporary), True, False), 1)
        self.assertIn("Missing script", self.output.getvalue())

    def test_piano_roll_environment_must_match_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            settings = Path(temporary) / "Settings"
            settings.mkdir()
            install_scripts(settings, True, False, False)
            with patch.dict("os.environ", {"FRUITFUL_PIANO_ROLL_DIR": temporary}):
                self.assertEqual(doctor(settings, True, True), 1)
        self.assertIn("does not match", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
