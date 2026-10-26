"""Local MCP tools for FL Studio."""

from __future__ import annotations

import math
import re

from fastmcp import FastMCP

from .bridge import Bridge, BridgeError
from .pianoroll import PianoRollBridge
from .sounds import search_freesound
from .styles import get_style, list_styles

mcp = FastMCP("Fruitful")

# One shared bridge for the process. Opened lazily on first call so the server can
# start even before FL/the virtual ports are ready.
_bridge = Bridge()
_piano_roll = PianoRollBridge()


@mcp.tool
def ping() -> dict:
    """Check the connection to FL Studio. Returns FL's version if reachable."""
    return _bridge.call("ping")


@mcp.tool
def get_channel_count() -> int:
    """Return the number of channels in the Channel Rack."""
    return _bridge.call("get_channel_count")


@mcp.tool
def set_step(channel: int, step: int, on: bool = True) -> str:
    """Toggle a single step in the step sequencer for a Channel Rack channel.

    Args:
        channel: Channel Rack index (0-based).
        step: Step index in the pattern (0-based).
        on: True to activate the step, False to clear it.
    """
    _bridge.call("set_grid_bit", channel=channel, step=step, value=1 if on else 0)
    return f"step {step} on channel {channel} {'set' if on else 'cleared'}"


@mcp.tool
def program_drum_pattern(channel: int, steps: list[bool]) -> str:
    """Write a full step-sequencer row for a channel (e.g. a kick or snare line).

    Args:
        channel: Channel Rack index (0-based).
        steps: list of on/off values, one per step (e.g. 16 booleans for a bar).
    """
    _bridge.call("program_pattern", channel=channel, steps=steps)
    return f"programmed {len(steps)} steps on channel {channel}"


@mcp.tool
def get_drum_pattern(channel: int, length: int = 16) -> list[bool]:
    """Read a step-sequencer row from a Channel Rack channel.

    Args:
        channel: Channel Rack index (0-based).
        length: Number of steps to read, from 1 to 64.
    """
    if not 1 <= length <= 64:
        raise ValueError("length must be between 1 and 64")
    return _bridge.call("get_pattern", channel=channel, length=length)


@mcp.tool
def set_channel_volume(channel: int, value: float) -> str:
    """Set a Channel Rack channel's volume.

    Args:
        channel: Channel Rack index (0-based).
        value: Volume from 0.0 (silent) to 1.0 (unity).
    """
    if not 0.0 <= value <= 1.0:
        raise ValueError("value must be between 0.0 and 1.0")
    _bridge.call("set_channel_volume", channel=channel, value=value)
    return f"channel {channel} volume set to {value:.3f}"


@mcp.tool
def set_channel_pan(channel: int, value: float) -> str:
    """Set a Channel Rack channel's pan.

    Args:
        channel: Channel Rack index (0-based).
        value: Pan from -1.0 (left) to 1.0 (right), with 0.0 centered.
    """
    if not -1.0 <= value <= 1.0:
        raise ValueError("value must be between -1.0 and 1.0")
    _bridge.call("set_channel_pan", channel=channel, value=value)
    return f"channel {channel} pan set to {value:.3f}"


@mcp.tool
def set_channel_name(channel: int, name: str) -> str:
    """Rename a Channel Rack channel.

    Args:
        channel: Channel Rack index (0-based).
        name: New channel name.
    """
    if not name.strip():
        raise ValueError("name must not be empty")
    _bridge.call("set_channel_name", channel=channel, name=name)
    return f"channel {channel} renamed to {name!r}"


@mcp.tool
def route_channel_to_mixer(channel: int, track: int) -> str:
    """Route a Channel Rack channel to a mixer track.

    Args:
        channel: Channel Rack index (0-based).
        track: Mixer track number as used by FL Studio.
    """
    _bridge.call("route_channel_to_mixer", channel=channel, track=track)
    return f"channel {channel} routed to mixer track {track}"


@mcp.tool
def get_plugin_params(index: int, slot: int = -1) -> list[dict]:
    """List the parameters exposed by a channel generator or mixer effect.

    Args:
        index: Channel Rack index for a generator, or mixer track index for an effect.
        slot: Mixer effect slot; leave at -1 for a Channel Rack generator.
    """
    first_page = _bridge.call("get_plugin_param_page", index=index, slot=slot, start=0, limit=32)
    params = first_page["params"]
    for start in range(len(params), first_page["total"], 32):
        params.extend(
            _bridge.call("get_plugin_param_page", index=index, slot=slot, start=start, limit=32)[
                "params"
            ]
        )
    return params


@mcp.tool
def get_plugin_param_page(index: int, start: int = 0, limit: int = 32, slot: int = -1) -> dict:
    """Read one bounded page of plugin parameters, for large instruments such as Surge XT.

    Args:
        index: Channel Rack index for a generator, or mixer track index for an effect.
        start: Zero-based first parameter index.
        limit: Number of parameters to return, from 1 to 64.
        slot: Mixer effect slot; leave at -1 for a Channel Rack generator.
    """
    if start < 0:
        raise ValueError("start must not be negative")
    if not 1 <= limit <= 64:
        raise ValueError("limit must be between 1 and 64")
    return _bridge.call("get_plugin_param_page", index=index, slot=slot, start=start, limit=limit)


@mcp.tool
def set_plugin_param(index: int, param: int, value: float, slot: int = -1) -> str:
    """Set a plugin parameter by its zero-based index.

    Args:
        index: Channel Rack index for a generator, or mixer track index for an effect.
        param: Zero-based plugin parameter index.
        value: Normalized parameter value from 0.0 to 1.0.
        slot: Mixer effect slot; leave at -1 for a Channel Rack generator.
    """
    if not 0.0 <= value <= 1.0:
        raise ValueError("value must be between 0.0 and 1.0")
    _bridge.call("set_plugin_param", index=index, param=param, value=value, slot=slot)
    return f"plugin parameter {param} set to {value:.3f}"


@mcp.tool
def get_project_state() -> dict:
    """Return a compact snapshot of Channel Rack channels and mixer tracks."""
    return _bridge.call("get_project_state")


@mcp.tool
def list_genre_starters() -> list[dict]:
    """List Fruitful's curated genre starter blueprints and their required sound roles."""
    return list_styles()


@mcp.tool
def get_genre_starter(style: str) -> dict:
    """Return a detailed, editable production plan for a genre starter.

    The plan includes target tempo, harmonic direction, required sound roles, section layout,
    and a production brief. It does not modify the current FL Studio project.
    """
    return get_style(style)


@mcp.tool
def search_cc0_sounds(query: str, limit: int = 10) -> dict:
    """Search Freesound for Creative Commons Zero sounds suited to a production role.

    Requires the free `FREESOUND_API_TOKEN` environment variable. Results are sound metadata
    and preview URLs only, cached locally for seven days; Fruitful never downloads or imports a
    sound without an explicit future user action.
    """
    return search_freesound(query, limit)


@mcp.tool
def get_tempo() -> float:
    """Return the current project tempo in BPM."""
    return _bridge.call("get_tempo")


@mcp.tool
def set_tempo(bpm: float) -> float:
    """Set the project tempo in BPM and return the tempo applied by FL Studio."""
    if not math.isfinite(bpm) or not 10 <= bpm <= 522:
        raise ValueError("bpm must be between 10 and 522")
    return _bridge.call("set_tempo", bpm=bpm)


_HOUSE_CHANNEL_PATTERNS = {
    "Kick": [True, False, False, False] * 4,
    "Clap": [False, False, False, False, True, False, False, False] * 2,
    "Closed Hat": [False, False, True, False] * 4,
}
_HOUSE_CHANNEL_ALIASES = {
    "Kick": ("kick",),
    "Clap": ("clap",),
    "Closed Hat": ("closed hat", "closedhat", "hi hat", "hihat"),
}


def _matches_drum_role(name: str, role: str) -> bool:
    normalized = " ".join(re.split(r"[\s_-]+", name.strip().casefold()))
    if role == "Closed Hat" and "open" in normalized.split():
        return False
    return any(
        normalized == alias or normalized.endswith(" " + alias)
        for alias in _HOUSE_CHANNEL_ALIASES[role]
    )


def _house_channel_indexes(channels: list[dict]) -> dict[str, int]:
    indexes = {}
    errors = []
    for role in _HOUSE_CHANNEL_ALIASES:
        matches = [channel for channel in channels if _matches_drum_role(channel["name"], role)]
        if len(matches) == 1:
            indexes[role] = matches[0]["index"]
        elif not matches:
            errors.append(f"no {role} channel")
        else:
            names = ", ".join(channel["name"] for channel in matches)
            errors.append(f"ambiguous {role} channels ({names})")
    if errors:
        available = ", ".join(
            channel["name"] or f"channel {channel['index']}" for channel in channels
        )
        raise ValueError(
            "Fruitful House Starter needs one unambiguous Kick, Clap, and Closed Hat channel. "
            f"Problems: {'; '.join(errors)}. Available: {available or 'none'}"
        )
    if len(set(indexes.values())) != len(indexes):
        raise ValueError("Use three separate channels named Kick, Clap, and Closed Hat.")
    return indexes


@mcp.tool
def start_house_beat(bpm: float = 124.0, play: bool = True) -> dict:
    """Program a one-bar four-on-the-floor house beat in a Fruitful House Starter template.

    The active FL project needs one each of Kick, Clap, and Closed Hat channels with loaded drum
    sounds. Names can include a sample prefix such as "808 Kick". This tool changes only those
    channels, sets the tempo, and can start playback. It does not create or replace instruments.

    Args:
        bpm: House tempo from 100 to 140 BPM. Defaults to 124.
        play: Start FL Studio playback after programming the bar. Defaults to True.
    """
    if not 100 <= bpm <= 140:
        raise ValueError("house beat bpm must be between 100 and 140")

    channels = _bridge.call("get_project_state")["channels"]
    indexes = _house_channel_indexes(channels)

    confirmed = []
    action = "write drums"
    try:
        for name, steps in _HOUSE_CHANNEL_PATTERNS.items():
            action = f"write {name}"
            _bridge.call("program_pattern", channel=indexes[name], steps=steps)
            action = f"check {name}"
            actual = _bridge.call("get_pattern", channel=indexes[name], length=16)
            if actual != steps:
                raise BridgeError(f"{name} did not match the requested pattern.")
            confirmed.append(name)
        action = "set tempo"
        applied_bpm = _bridge.call("set_tempo", bpm=bpm)
        if (
            not isinstance(applied_bpm, (int, float))
            or not math.isfinite(applied_bpm)
            or abs(applied_bpm - bpm) > 0.01
        ):
            raise BridgeError("FL did not confirm the requested tempo.")
        if play:
            action = "start playback"
            _bridge.call("transport", action="play")
    except BridgeError as error:
        raise BridgeError(
            f"Could not {action}. Confirmed drum rows: {', '.join(confirmed) or 'none'}. "
            f"Other changes may have applied; inspect the current pattern before retrying. {error}"
        ) from error
    return {
        "bpm": applied_bpm,
        "channels": indexes,
        "playing": play,
        "drums_verified": True,
    }


def _validated_notes(notes: list[dict]) -> list[dict]:
    if not 1 <= len(notes) <= 4096:
        raise ValueError("Supply 1 to 4096 notes. Empty writes are not allowed.")
    validated = []
    for index, note in enumerate(notes):
        try:
            number = note["number"]
            time = float(note["time"])
            length = float(note["length"])
            velocity = float(note.get("velocity", 0.8))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"note {index} must include numeric number, time, and length"
            ) from error
        if type(number) is not int or not 0 <= number <= 127:
            raise ValueError(f"note {index} number must be between 0 and 127")
        if not math.isfinite(time) or time < 0:
            raise ValueError(f"note {index} time must not be negative")
        if not math.isfinite(length) or length <= 0:
            raise ValueError(f"note {index} length must be greater than zero")
        if not 0 <= velocity <= 1:
            raise ValueError(f"note {index} velocity must be between 0 and 1")
        validated.append({"number": number, "time": time, "length": length, "velocity": velocity})
    return validated


@mcp.tool
def get_piano_roll_notes() -> list[dict]:
    """Read the notes in the Piano Roll currently open in FL Studio.

    Each note includes MIDI number (60 is middle C), start time and length in beats, and
    velocity from 0.0 to 1.0. Keep the intended instrument's Piano Roll open.
    """
    return _piano_roll.call("get_notes")


@mcp.tool
def write_piano_roll_notes(notes: list[dict], mode: str = "add") -> list[dict]:
    """Add or replace notes in the Piano Roll currently open in FL Studio.

    Args:
        notes: Notes with MIDI number (0-127), time in beats, length in beats, and optional
            velocity (0.0-1.0). Notes at the same time form a chord.
        mode: "add" preserves current notes; "replace" clears them before writing the supplied notes.
    """
    if mode not in {"add", "replace"}:
        raise ValueError('mode must be "add" or "replace"')
    return _piano_roll.call(f"{mode}_notes", notes=_validated_notes(notes))


@mcp.tool
def transport(action: str) -> str:
    """Control FL Studio playback.

    Args:
        action: One of "play", "stop", or "record".
    """
    if action not in {"play", "stop", "record"}:
        raise ValueError('action must be one of "play", "stop", or "record"')
    _bridge.call("transport", action=action)
    return f"transport {action} sent"


def main() -> None:
    """Keep the module entry point consistent with the installed CLI."""
    from .cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
