"""Check command arguments before opening MIDI or changing an FL project."""

import math


def validate_command(cmd: str, args: dict) -> None:
    for name in ("channel", "index", "param", "track", "start", "step", "length", "limit", "slot"):
        if name not in args:
            continue
        value = args[name]
        if name == "slot":
            minimum = -1
        elif name in {"length", "limit"}:
            minimum = 1
        else:
            minimum = 0
        if type(value) is not int or value < minimum:
            raise ValueError(f"{name} must be an integer of at least {minimum}.")
        if name == "step" and value > 63:
            raise ValueError("step must be between 0 and 63.")
        if name in {"length", "limit"} and value > 64:
            raise ValueError(f"{name} must be between 1 and 64.")
    if "value" in args:
        value = args["value"]
        minimum = -1 if cmd == "set_channel_pan" else 0
        if type(value) not in {int, float} or not math.isfinite(value) or not minimum <= value <= 1:
            raise ValueError(f"value must be a finite number between {minimum} and 1.")
    if "bpm" in args:
        bpm = args["bpm"]
        if type(bpm) not in {int, float} or not math.isfinite(bpm) or not 10 <= bpm <= 522:
            raise ValueError("bpm must be between 10 and 522.")
    if cmd == "program_pattern":
        steps = args.get("steps")
        if (
            not isinstance(steps, list)
            or not 1 <= len(steps) <= 64
            or any(type(step) is not bool for step in steps)
        ):
            raise ValueError("A drum row needs 1 to 64 true/false steps.")
    if cmd == "set_channel_name":
        name = args.get("name")
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            raise ValueError("name must contain 1 to 80 characters.")
