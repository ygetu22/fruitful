# name=Fruitful
# url=https://github.com/  (TBD)
# supportedDevices=Fruitful Request
"""Fruitful device script — runs INSIDE FL Studio's MIDI scripting sandbox.

Install: copy this file into a subfolder of FL's MIDI scripts directory, e.g.
    .../Image-Line/FL Studio/Settings/Hardware/Fruitful/device_Fruitful.py
then in FL: Options > MIDI Settings, assign the "Fruitful Request" input to this
"Fruitful" controller type, and enable it.

It receives Fruitful SysEx commands on the Request port, calls FL's native API, and
sends results back as SysEx on the output (Response) port.

NOTE: the protocol here is mirrored from src/fruitful/protocol.py — keep them in sync.
The sandbox can't import our package, so the logic is inlined and dependency-free
(stdlib `json` only).
"""

import json

import channels
import device
import general
import transport  # noqa: F401  (reserved for later milestones)

MANUFACTURER_ID = 0x7D
DIR_REQUEST = 0x01
DIR_RESPONSE = 0x02


def OnInit():
    """Called by FL when the script loads."""
    print("Fruitful device script loaded.")


def OnDeInit():
    print("Fruitful device script unloaded.")


def OnSysEx(event):
    """Inbound SysEx handler. `event.sysex` includes the F0..F7 framing."""
    data = list(event.sysex)
    if data and data[0] == 0xF0:
        data = data[1:]
    if data and data[-1] == 0xF7:
        data = data[:-1]
    if len(data) < 2 or data[0] != MANUFACTURER_ID or data[1] != DIR_REQUEST:
        return  # not a Fruitful request
    try:
        req = json.loads(bytes(data[2:]).decode("ascii"))
    except Exception:
        return
    _handle(req)


def _send_response(payload):
    text = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    frame = bytes([0xF0, MANUFACTURER_ID, DIR_RESPONSE] + [ord(c) for c in text] + [0xF7])
    device.midiOutSysex(frame)


def _handle(req):
    rid = req.get("id")
    cmd = req.get("cmd")
    args = req.get("args") or {}
    try:
        result = _dispatch(cmd, args)
        _send_response({"id": rid, "ok": True, "result": result})
    except Exception as e:  # surface the error back to the client, never crash the script
        _send_response({"id": rid, "ok": False, "error": str(e)})


def _dispatch(cmd, args):
    if cmd == "ping":
        return {"pong": True, "fl_version": general.getVersion()}

    if cmd == "get_channel_count":
        return channels.channelCount()

    if cmd == "set_grid_bit":
        channels.setGridBit(args["channel"], args["step"], args["value"])
        return None

    if cmd == "program_pattern":
        ch = args["channel"]
        for i, value in enumerate(args["steps"]):
            channels.setGridBit(ch, i, 1 if value else 0)
        return None

    raise ValueError("unknown cmd: %r" % cmd)
