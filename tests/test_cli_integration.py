"""Exercise the installed CLI and MCP startup without touching FL Studio."""

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

EXECUTABLE = str(Path(sys.executable).with_name("fruitful"))


class InstalledCliTests(unittest.TestCase):
    def run_cli(self, *arguments, cwd):
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        return subprocess.run(
            [EXECUTABLE, *arguments],
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_help_version_and_unknown_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            for arguments in [
                ("--help",),
                ("--version",),
                ("install-scripts", "--help"),
                ("doctor", "--help"),
            ]:
                result = self.run_cli(*arguments, cwd=temporary)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Starting MCP", result.stderr)
            result = self.run_cli("unknown-command", cwd=temporary)
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid choice", result.stderr)

    def test_guided_setup_with_explicit_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            settings = Path(temporary) / "Settings"
            settings.mkdir()
            result = self.run_cli("setup", "--settings-dir", str(settings), cwd=temporary)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((settings / "Hardware/Fruitful/device_Fruitful.py").is_file())
            self.assertIn("Command:", result.stdout)
            self.assertNotIn("Piano Roll", result.stdout)

    def test_install_preview_install_repeat_and_conflict(self):
        with tempfile.TemporaryDirectory(prefix="fruitful cli ያ ") as temporary:
            settings = Path(temporary) / "FL Studio/Settings"
            settings.mkdir(parents=True)
            arguments = ("install-scripts", "--settings-dir", str(settings), "--piano-roll")
            result = self.run_cli(*arguments, "--dry-run", cwd=temporary)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(settings.iterdir()), [])
            result = self.run_cli(*arguments, cwd=temporary)
            self.assertEqual(result.returncode, 0, result.stderr)
            device = settings / "Hardware/Fruitful/device_Fruitful.py"
            piano = settings / "Piano roll scripts/Fruitful Apply.pyscript"
            self.assertTrue(device.is_file())
            self.assertIn(repr(str(piano.parent.resolve())), piano.read_text())
            result = self.run_cli(*arguments, cwd=temporary)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.count("Already installed"), 2)
            device.write_text("# preserve local changes\n")
            result = self.run_cli(*arguments, cwd=temporary)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(device.read_text(), "# preserve local changes\n")
            result = self.run_cli(*arguments, "--force", cwd=temporary)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("# name=Fruitful", device.read_text())


class McpStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_argument_stdio_handshake_and_local_tool(self):
        # A real protocol client, with no model access and no FL write tools called.
        with (
            tempfile.TemporaryDirectory() as temporary,
            tempfile.TemporaryFile(mode="w+") as errors,
        ):
            parameters = StdioServerParameters(command=EXECUTABLE, cwd=temporary)
            async with asyncio.timeout(30):
                async with stdio_client(parameters, errlog=errors) as (reader, writer):
                    async with ClientSession(reader, writer) as session:
                        initialized = await session.initialize()
                        self.assertEqual(initialized.serverInfo.name, "Fruitful")
                        tools = await session.list_tools()
                        names = {tool.name for tool in tools.tools}
                        self.assertTrue({"ping", "get_project_state", "start_house_beat"} <= names)
                        result = await session.call_tool("list_genre_starters", {})
                        self.assertFalse(result.isError)
                        self.assertTrue(result.content)


if __name__ == "__main__":
    unittest.main()
