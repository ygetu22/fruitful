"""The Fruitful MCP server.

Exposes tools to Claude (or any MCP client) and forwards them across the bridge to
FL Studio. This is the Milestone-1 surface: enough to prove the round-trip end to end.
More tools (mixer, plugin params, project state) land in later milestones — see SPEC.md.
"""

from __future__ import annotations

from fastmcp import FastMCP

from .bridge import Bridge

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


def main() -> None:
    """Entry point — runs the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
