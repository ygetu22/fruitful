"""The Fruitful bridge client.

Opens Fruitful's virtual MIDI port, sends commands to FL Studio as SysEx, and
awaits the matching reply on that same duplex port.

Communication is request/response with `id` correlation: `call()` sends a frame and
blocks until a Response frame with the same `id` arrives (or it times out — which
almost always means the device script isn't installed/running in FL).
"""

from __future__ import annotations

import itertools
import queue
import threading

import mido

from . import protocol

REQUEST_PORT = "Fruitful Request"
# FL sends from a device script to the output linked to that same device. The
# request bus is therefore duplex; protocol directions distinguish replies.
RESPONSE_PORT = REQUEST_PORT
DEFAULT_TIMEOUT = 5.0


class BridgeError(RuntimeError):
    """A command failed inside FL, or the bridge could not be used."""


class BridgeTimeout(BridgeError):
    """No response arrived in time — is the Fruitful device script running in FL?"""


def _find_port(substring: str, names: list[str]) -> str:
    """Match a configured port name against the OS's actual port names.

    MIDI backends often append/prepend text to port names, so we match by substring.
    """
    for name in names:
        if substring.lower() in name.lower():
            return name
    raise BridgeError(
        f"MIDI port matching {substring!r} not found. "
        f"Create the Fruitful virtual MIDI ports first (macOS: IAC Driver). "
        f"Available ports: {names or 'none'}"
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
        self._ids = itertools.count(1)
        self._pending: dict[int, queue.Queue] = {}
        self._lock = threading.Lock()
        self._out = None
        self._in = None

    # -- lifecycle ---------------------------------------------------------

    def open(self) -> None:
        if self._out is not None:
            return
        out_name = _find_port(self._request_port, mido.get_output_names())
        in_name = _find_port(self._response_port, mido.get_input_names())
        self._out = mido.open_output(out_name)
        self._in = mido.open_input(in_name, callback=self._on_message)

    def close(self) -> None:
        if self._in is not None:
            self._in.close()
            self._in = None
        if self._out is not None:
            self._out.close()
            self._out = None

    # -- receive -----------------------------------------------------------

    def _on_message(self, msg) -> None:
        if msg.type != "sysex":
            return
        try:
            direction, payload = protocol.decode(list(msg.data))
        except Exception:
            return  # not ours / malformed
        if direction != protocol.DIR_RESPONSE:
            return
        mid = payload.get("id")
        with self._lock:
            q = self._pending.get(mid)
        if q is not None:
            q.put(payload)

    # -- send --------------------------------------------------------------

    def call(self, cmd: str, **args):
        """Send a command and return its result, or raise BridgeError on failure."""
        if self._out is None:
            self.open()

        mid = next(self._ids)
        reply: queue.Queue = queue.Queue(maxsize=1)
        with self._lock:
            self._pending[mid] = reply

        data = protocol.encode(protocol.DIR_REQUEST, {"id": mid, "cmd": cmd, "args": args})
        self._out.send(mido.Message("sysex", data=data))

        try:
            payload = reply.get(timeout=self._timeout)
        except queue.Empty:
            raise BridgeTimeout(
                f"No response to {cmd!r} within {self._timeout}s. "
                f"Is FL Studio open with the Fruitful device script enabled?"
            )
        finally:
            with self._lock:
                self._pending.pop(mid, None)

        if not payload.get("ok"):
            raise BridgeError(payload.get("error", "unknown error from FL"))
        return payload.get("result")
