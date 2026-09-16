# name=Fruitful
# url=https://github.com/  (TBD)
# supportedDevices=Fruitful Request
"""Fruitful device script — runs INSIDE FL Studio's MIDI scripting sandbox.

Install: copy this file into a subfolder of FL's MIDI scripts directory, e.g.
    .../Image-Line/FL Studio/Settings/Hardware/Fruitful/device_Fruitful.py
then in FL: Options > MIDI Settings, assign the "Fruitful Request" input to this
"Fruitful" controller type, and enable it.

It receives Fruitful SysEx commands on its linked MIDI port, calls FL's native API,
and sends results back as SysEx on that same duplex port.

NOTE: the protocol here is mirrored from src/fruitful/protocol.py — keep them in sync.
The sandbox can't import our package, so the logic is inlined and dependency-free
(stdlib `json` only).
"""

import json

import channels
import device
import general
import mixer
import plugins
import transport

MANUFACTURER_ID = 0x7D
DIR_REQUEST = 0x01
DIR_RESPONSE = 0x02


def OnInit():
    """Called by FL when the script loads."""
    print("Fruitful device script loaded.")


def OnDeInit():
    print("Fruitful device script unloaded.")


def _receive_sysex(raw):
    """Process one FL SysEx payload, including its optional F0/F7 framing."""
    if raw is None:
        return
    data = list(raw)
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


def OnMidiIn(event):
    """Handle raw SysEx before FL dispatches it to the generic MIDI handlers."""
    if event.sysex is not None:
        _receive_sysex(event.sysex)
        event.handled = True


def OnSysEx(event):
    """Fallback SysEx handler for FL versions that skip OnMidiIn processing."""
    _receive_sysex(event.sysex)


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

    if cmd == "set_channel_volume":
        channels.setChannelVolume(args["channel"], args["value"])
        return None

    if cmd == "set_channel_pan":
        channels.setChannelPan(args["channel"], args["value"])
        return None

    if cmd == "set_channel_name":
        channels.setChannelName(args["channel"], args["name"])
        return None

    if cmd == "route_channel_to_mixer":
        channels.setTargetFxTrack(args["channel"], args["track"])
        return None

    if cmd == "get_plugin_params":
        index = args["index"]
        slot = args.get("slot", -1)
        if not plugins.isValid(index, slot):
            raise ValueError("no valid plugin at index %r, slot %r" % (index, slot))
        count = plugins.getParamCount(index, slot)
        params = []
        for i in range(count):
            try:
                value_string = plugins.getParamValueString(i, index, slot)
            except Exception:
                # FL only supports the formatted value for some plugins.
                value_string = None
            params.append(
                {
                    "index": i,
                    "name": plugins.getParamName(i, index, slot),
                    "value": plugins.getParamValue(i, index, slot),
                    "value_string": value_string,
                }
            )
        return params

    if cmd == "set_plugin_param":
        index = args["index"]
        slot = args.get("slot", -1)
        value = args["value"]
        if not 0.0 <= value <= 1.0:
            raise ValueError("plugin value must be between 0.0 and 1.0")
        result = plugins.setParamValue(value, args["param"], index, slot)
        return {"value": result}

    if cmd == "get_project_state":
        channel_count = channels.channelCount()
        channels_state = []
        for i in range(channel_count):
            channels_state.append(
                {
                    "index": i,
                    "name": channels.getChannelName(i),
                    "volume": channels.getChannelVolume(i),
                    "pan": channels.getChannelPan(i),
                    "muted": bool(channels.isChannelMuted(i)),
                    "solo": bool(channels.isChannelSolo(i)),
                    "mixer_track": channels.getTargetFxTrack(i),
                }
            )

        track_count = mixer.getTrackCount()
        mixer_state = []
        for i in range(track_count):
            mixer_state.append(
                {
                    "index": i,
                    "name": mixer.getTrackName(i),
                    "volume": mixer.getTrackVolume(i),
                    "pan": mixer.getTrackPan(i),
                    "muted": bool(mixer.isTrackMuted(i)),
                    "solo": bool(mixer.isTrackSolo(i)),
                }
            )
        return {"channels": channels_state, "mixer_tracks": mixer_state}

    if cmd == "transport":
        action = args["action"]
        if action == "play":
            transport.start()
            return None
        if action == "stop":
            transport.stop()
            return None
        if action == "record":
            transport.record()
            return None
        raise ValueError("unknown transport action: %r" % action)

    raise ValueError("unknown cmd: %r" % cmd)
