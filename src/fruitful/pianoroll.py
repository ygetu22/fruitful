"""Bridge to Fruitful's experimental FL Studio Piano Roll script."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from uuid import uuid4


class PianoRollError(RuntimeError):
    """The Piano Roll script could not complete an operation."""


class PianoRollBridge:
    def __init__(self, timeout: float = 5.0):
        self._timeout = timeout
        self._lock = threading.Lock()

    @staticmethod
    def _script_dir() -> Path:
        configured = os.environ.get("FRUITFUL_PIANO_ROLL_DIR")
        path = (
            Path(configured).expanduser()
            if configured
            else Path.home() / "Documents/Image-Line/FL Studio/Settings/Piano roll scripts"
        )
        if not path.is_dir():
            raise PianoRollError(
                f"Piano Roll scripts folder not found at {path}. "
                "Set FRUITFUL_PIANO_ROLL_DIR to FL Studio's Piano roll scripts folder."
            )
        return path

    @staticmethod
    def _trigger() -> None:
        app_name = os.environ.get("FRUITFUL_FL_APP", "FL Studio")
        process_name = os.environ.get("FRUITFUL_FL_PROCESS", "OsxFL")
        script = (
            f"tell application {json.dumps(app_name, ensure_ascii=False)} to activate\n"
            "delay 0.5\n"
            'tell application "System Events"\n'
            f"tell process {json.dumps(process_name, ensure_ascii=False)} to set frontmost to true\n"
            'keystroke "y" using {command down, option down}\n'
            "end tell"
        )
        try:
            completed = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            raise PianoRollError(
                "FL's keyboard trigger timed out. Check the MCP client's Automation permission."
            ) from None
        if completed.returncode:
            raise PianoRollError(
                f"Could not trigger the Piano Roll script: {completed.stderr.strip()}. "
                "Check the MCP client's Accessibility permission, focus the intended Piano Roll, "
                "and run Fruitful Apply once from its scripts menu."
            )

    def _wait_for_response(self, path: Path, request_id: str):
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            try:
                response = json.loads(path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                response = None
            if isinstance(response, dict) and response.get("id") == request_id:
                if response.get("ok") is not True:
                    raise PianoRollError(response.get("error", "The Piano Roll script failed."))
                return response.get("result")
            time.sleep(0.05)
        raise PianoRollError(
            "The Piano Roll script did not respond. Changes may have applied; read the notes before retrying. "
            "Check the intended Piano Roll is focused and Fruitful Apply is the remembered script."
        )

    def call(self, action: str, **args):
        with self._lock:
            directory = self._script_dir()
            request_path = directory / "fruitful_request.json"
            response_path = directory / "fruitful_response.json"
            temporary_path = request_path.with_suffix(".tmp")
            request_id = str(uuid4())
            try:
                temporary_path.write_text(
                    json.dumps({"id": request_id, "action": action, "args": args}, allow_nan=False),
                    encoding="utf-8",
                )
                temporary_path.replace(request_path)
                self._trigger()
                return self._wait_for_response(response_path, request_id)
            finally:
                temporary_path.unlink(missing_ok=True)
                try:
                    pending = json.loads(request_path.read_text(encoding="utf-8"))
                except (FileNotFoundError, json.JSONDecodeError):
                    pending = None
                if isinstance(pending, dict) and pending.get("id") == request_id:
                    request_path.unlink(missing_ok=True)
