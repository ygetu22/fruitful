"""Request/response MIDI bridge. Commands are serialized and never retried automatically."""

from __future__ import annotations

import itertools
import queue
import secrets
import threading

import mido

from . import protocol
from .validation import validate_command

REQUEST_PORT = "Fruitful Request"
RESPONSE_PORT = REQUEST_PORT
DEFAULT_TIMEOUT = 5.0


class BridgeError(RuntimeError):
    """FL rejected a command, or the MIDI connection failed."""


class BridgeTimeout(BridgeError):
    """FL did not confirm whether the command was applied."""


def _find_port(substring: str, names: list[str]) -> str:
    exact = [name for name in names if name.casefold() == substring.casefold()]
    matches = exact or [name for name in names if substring.casefold() in name.casefold()]
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise BridgeError(
            f"More than one MIDI port matches {substring!r}. Keep one Fruitful Request bus enabled."
        )
    raise BridgeError(
        f"MIDI port {substring!r} not found. Enable the IAC Driver and create a Fruitful Request bus."
    )


class Bridge:
    def __init__(
        self,
        request_port: str = REQUEST_PORT,
        response_port: str = RESPONSE_PORT,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self._request_port = request_port
        self._response_port = response_port
        self._timeout = timeout
        # Separate clients can share the bus; their replies must not share request IDs.
        self._ids = itertools.count(secrets.randbits(48) + 1)
        self._pending: dict[int, queue.Queue] = {}
        self._lock = threading.Lock()
        self._io_lock = threading.RLock()
        self._out = None
        self._in = None

    def open(self) -> None:
        with self._io_lock:
            if self._out is not None:
                return
            try:
                out_name = _find_port(self._request_port, mido.get_output_names())
                in_name = _find_port(self._response_port, mido.get_input_names())
                self._out = mido.open_output(out_name)
                self._in = mido.open_input(in_name, callback=self._on_message)
            except Exception as error:
                self.close()
                raise BridgeError(
                    f"Could not open the MIDI connection: {error}. Run fruitful doctor."
                ) from error

    def close(self) -> None:
        with self._io_lock:
            ports = [self._in, self._out]
            self._in = self._out = None
            for port in ports:
                if port is not None:
                    try:
                        port.close()
                    except (OSError, RuntimeError):
                        pass  # A disconnected port may already be closed by its backend.

    def _on_message(self, msg) -> None:
        if msg.type != "sysex":
            return
        try:
            direction, payload = protocol.decode(list(msg.data))
        except (ValueError, TypeError, UnicodeError):
            return
        if direction != protocol.DIR_RESPONSE or not isinstance(payload, dict):
            return
        mid = payload.get("id")
        if type(mid) is not int:
            return
        with self._lock:
            reply = self._pending.get(mid)
        if reply is not None:
            try:
                reply.put_nowait(payload)
            except queue.Full:
                pass  # Duplicate responses must not block the MIDI callback.

    def call(self, cmd: str, **args):
        validate_command(cmd, args)
        with self._io_lock:
            mid = next(self._ids)
            data = protocol.encode(protocol.DIR_REQUEST, {"id": mid, "cmd": cmd, "args": args})
            self.open()
            reply: queue.Queue = queue.Queue(maxsize=1)
            with self._lock:
                self._pending[mid] = reply
            try:
                try:
                    self._out.send(mido.Message("sysex", data=data))
                except (OSError, RuntimeError) as error:
                    self.close()
                    raise BridgeError(
                        "MIDI connection lost. FL may have applied the command. "
                        "Run fruitful doctor and read the project state before retrying."
                    ) from error
                try:
                    payload = reply.get(timeout=self._timeout)
                except queue.Empty:
                    self.close()
                    raise BridgeTimeout(
                        f"FL did not confirm {cmd!r} within {self._timeout}s. "
                        "Check that FL is open and Fruitful is enabled. "
                        "The command may have been applied; read the project state before retrying."
                    ) from None
            finally:
                with self._lock:
                    self._pending.pop(mid, None)
            if payload.get("ok") is not True:
                raise BridgeError(payload.get("error", "FL rejected the command."))
            return payload.get("result")
