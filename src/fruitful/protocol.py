"""Fruitful SysEx wire protocol — shared encode/decode.

A Fruitful frame on the wire is:

    F0  7D  <direction>  <ascii-json payload...>  F7

  * F0 / F7        SysEx start / end (added by mido; not part of `data`).
  * 7D             SysEx manufacturer ID reserved for non-commercial / educational use.
  * <direction>    0x01 = request (server -> FL), 0x02 = response (FL -> server).
  * <payload>      the command/result object as ASCII JSON.

ASCII JSON is the trick that keeps this simple: every byte between F0 and F7 must be
7-bit (0x00-0x7F), and `json.dumps(..., ensure_ascii=True)` emits only ASCII bytes
(non-ASCII becomes \\uXXXX escapes). So the JSON string drops straight into the SysEx
payload with no extra encoding layer.

This module is the source of truth for the protocol. The FL device script
(`device/device_Fruitful.py`) mirrors this logic inline because it cannot import this
package from inside FL's sandbox — keep the two in sync.
"""

from __future__ import annotations

import json

MANUFACTURER_ID = 0x7D
DIR_REQUEST = 0x01
DIR_RESPONSE = 0x02


def encode(direction: int, payload: dict) -> list[int]:
    """Encode a payload dict into SysEx *data* bytes (excluding the F0/F7 framing)."""
    text = json.dumps(payload, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    # ensure_ascii guarantees every char is < 0x80, so ord() yields valid SysEx data bytes.
    return [MANUFACTURER_ID, direction, *[ord(c) for c in text]]


def decode(data: list[int]) -> tuple[int, dict]:
    """Decode SysEx *data* bytes (excluding F0/F7) into (direction, payload)."""
    if len(data) < 2 or data[0] != MANUFACTURER_ID:
        raise ValueError("not a Fruitful SysEx frame")
    direction = data[1]
    text = bytes(data[2:]).decode("ascii")
    return direction, json.loads(text)
