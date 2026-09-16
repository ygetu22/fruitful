"""The Fruitful MCP server.

Exposes tools to Claude (or any MCP client) and forwards them across the bridge to
FL Studio.
"""

from __future__ import annotations

import sys

from fastmcp import FastMCP

from .bridge import Bridge, BridgeError

mcp = FastMCP("Fruitful")

# One shared bridge for the process. Opened lazily on first call so the server can
# start even before FL/the virtual ports are ready.
_bridge = Bridge()


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
    _bridge.call("program_pattern", channel=channel, steps=[bool(s) for s in steps])
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
    return _bridge.call("get_plugin_params", index=index, slot=slot)


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
def transport(action: str) -> str:
    """Control FL Studio playback.

    Args:
        action: One of "play", "stop", or "record".
    """
    if action not in {"play", "stop", "record"}:
        raise ValueError('action must be one of "play", "stop", or "record"')
    _bridge.call("transport", action=action)
    return f"transport {action} sent"


def doctor() -> None:
    """Check that Fruitful can reach its FL Studio device script."""
    try:
        result = Bridge().call("ping")
    except BridgeError as error:
        print(f"Fruitful doctor: {error}")
        raise SystemExit(1) from error
    print(f"Fruitful doctor: connected to FL Studio (MIDI scripting version {result['fl_version']})")


def main() -> None:
    """Run the MCP server, or perform a local connection check."""
    if sys.argv[1:] == ["doctor"]:
        doctor()
        return
    mcp.run()


if __name__ == "__main__":
    main()
