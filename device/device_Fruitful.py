# name=Fruitful
# url=https://github.com/ygetu22/fruitful
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
import math

import channels
import general
import mixer
import plugins
import transport

import device

MANUFACTURER_ID = 0x7D
DIR_REQUEST = 0x01
DIR_RESPONSE = 0x02
TEMPO_SCALE = 1000


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
    if not isinstance(req, dict):
        return
    rid = req.get("id")
    cmd = req.get("cmd")
    args = req.get("args") or {}
    try:
        if not isinstance(cmd, str) or not isinstance(args, dict):
            raise ValueError("A command needs a name and an argument object.")
        result = _dispatch(cmd, args)
        _send_response({"id": rid, "ok": True, "result": result})
    except Exception as e:  # surface the error back to the client, never crash the script
        _send_response({"id": rid, "ok": False, "error": str(e)})


def _plugin_param_page(index, slot, start, limit):
    if not plugins.isValid(index, slot):
        raise ValueError("no valid plugin at index %r, slot %r" % (index, slot))
    if start < 0:
        raise ValueError("start must not be negative")
    if not 1 <= limit <= 64:
        raise ValueError("limit must be between 1 and 64")
    total = plugins.getParamCount(index, slot)
    params = []
    for i in range(start, min(start + limit, total)):
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
    return {"total": total, "start": start, "params": params}


def _dispatch(cmd, args):
    if "channel" in args:
        channel = args["channel"]
        if type(channel) is not int or not 0 <= channel < channels.channelCount():
            raise ValueError(
                "Channel no longer exists. Read the project state and choose a channel again."
            )
    if cmd == "set_grid_bit":
        if (
            type(args.get("step")) is not int
            or not 0 <= args["step"] <= 63
            or args.get("value") not in (0, 1)
        ):
            raise ValueError("Use a step from 0 to 63 and a value of 0 or 1.")
    if cmd == "program_pattern":
        steps = args.get("steps")
        if (
            not isinstance(steps, list)
            or not 1 <= len(steps) <= 64
            or any(type(step) is not bool for step in steps)
        ):
            raise ValueError("A drum row needs 1 to 64 true/false steps.")
    if cmd == "get_pattern":
        length = args.get("length", 16)
        if type(length) is not int or not 1 <= length <= 64:
            raise ValueError("length must be between 1 and 64.")
    if cmd in ("set_channel_volume", "set_channel_pan", "set_plugin_param"):
        value = args.get("value")
        minimum = -1 if cmd == "set_channel_pan" else 0
        if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= 1:
            raise ValueError("Control value is outside its allowed range.")
    if cmd == "set_channel_name":
        name = args.get("name")
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            raise ValueError("name must contain 1 to 80 characters.")
    if cmd == "route_channel_to_mixer":
        track = args.get("track")
        if type(track) is not int or not 0 <= track < mixer.getTrackCount():
            raise ValueError("Mixer track no longer exists. Read the project state again.")
    if cmd == "set_tempo":
        bpm = args.get("bpm")
        if type(bpm) not in (int, float) or not math.isfinite(bpm) or not 10 <= bpm <= 522:
            raise ValueError("bpm must be between 10 and 522.")
    if cmd in ("set_plugin_param", "get_plugin_param_page", "get_plugin_params"):
        index = args.get("index")
        slot = args.get("slot", -1)
        if (
            type(index) is not int
            or index < 0
            or type(slot) is not int
            or slot < -1
            or not plugins.isValid(index, slot)
        ):
            raise ValueError("Plugin no longer exists. Inspect the plugin again.")
        if cmd == "set_plugin_param":
            param = args.get("param")
            if type(param) is not int or not 0 <= param < plugins.getParamCount(index, slot):
                raise ValueError("Plugin parameter no longer exists. Inspect the plugin again.")

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

    if cmd == "get_pattern":
        ch = args["channel"]
        length = args.get("length", 16)
        return [bool(channels.getGridBit(ch, i)) for i in range(length)]

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
        return _plugin_param_page(index, slot, 0, 64)["params"]

    if cmd == "get_plugin_param_page":
        return _plugin_param_page(
            args["index"], args.get("slot", -1), args.get("start", 0), args.get("limit", 32)
        )

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

    if cmd == "get_tempo":
        # FL represents the tempo as BPM multiplied by 1,000 in its script API.
        return mixer.getCurrentTempo() / TEMPO_SCALE

    if cmd == "set_tempo":
        mixer.setCurrentTempo(round(args["bpm"] * TEMPO_SCALE))
        return mixer.getCurrentTempo() / TEMPO_SCALE

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
