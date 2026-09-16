# Fruitful — Technical Specification

Version 0.1 (draft) · 2026-06-14

This document defines how Fruitful is built. It is the source of truth for the architecture, the wire protocol,
and the milestone plan. Implementation details and a file-by-file guide live in [`NOTES.md`](./NOTES.md).

---

## 1. Goals & non-goals

**Goals**
- Connect Claude (or any MCP client) to FL Studio for natural-language music production.
- Be **reliable**: build only on FL's directly-supported native scripting API, so every action is deterministic.
- Cover the full set of natively supported capabilities — plugin-parameter control, channel routing, and
  project-state awareness — not only drum patterns.

**Non-goals (v1)**
- Writing notes/chords/melodies into the **piano roll**. FL's API exposes no native persistent note-write
  function, so this is deferred until/unless Image-Line adds one.
- Arrangement/playlist authoring (arrangement module is largely read-only).

---

## 2. The core constraint

FL Studio's MIDI Controller Scripting runs inside FL in a **stripped-down, sandboxed Python interpreter** that
blocks operations which could alter the user's PC. As a result, **sockets and file I/O are unreliable/unsupported
inside the device script.** The only universally reliable channel in and out of the script is **MIDI**.

Standard MIDI note messages carry only 7-bit values, which is limiting for arbitrary structured data. Fruitful
instead uses **System Exclusive (SysEx)** messages, whose payload is an arbitrary-length byte stream. That lets
it send *structured commands* and receive *return values* without that limitation.

This general approach is demonstrated by [Flapi](https://github.com/MaddyGuthridge/Flapi), which we credit as
prior art. As Flapi is currently unmaintained, Fruitful implements its own focused bridge scoped to its command
set.

---

## 3. Architecture

```
┌─────────────────┐   MCP (stdio)   ┌────────────────────────┐   SysEx over    ┌──────────────────────────┐
│  Claude Desktop │ ───────────────▶│   Fruitful MCP server  │  virtual MIDI   │  Fruitful device script  │
│  (MCP client)   │ ◀───────────────│   (FastMCP, normal     │ ───────────────▶│  (inside FL's sandbox)   │
└─────────────────┘                 │    Python process)     │ ◀───────────────│                          │
                                      └────────────────────────┘  duplex MIDI port └───────────┬─────────────┘
                                                                                                 │ native API calls
                                                                                              ▼
                                                                                   ┌──────────────────────┐
                                                                                   │   FL Studio engine    │
                                                                                   └──────────────────────┘
```

Three components:

1. **MCP server** (`src/fruitful/server.py`) — a FastMCP server exposing tools to Claude. Translates tool calls
   into Fruitful commands and sends them over the bridge.
2. **Bridge client** (`src/fruitful/bridge.py`) — opens the virtual MIDI ports via `mido`/`python-rtmidi`,
   encodes commands to SysEx, sends on the Request port, awaits the matching reply on the Response port.
3. **Device script** (`device/device_Fruitful.py`) — installed into FL's MIDI scripts folder. Receives SysEx,
   decodes the command, calls the native FL API (`channels`, `mixer`, `plugins`, `transport`, …), and sends the
   result back as SysEx.

### Virtual MIDI ports

- One duplex port: **`Fruitful Request`** carries both commands and replies; the SysEx direction byte
  distinguishes them.
- On **macOS** it is created with the built-in **IAC Driver** (Audio MIDI Setup) — no third-party tool.
- On Windows a loopback tool (e.g. loopMIDI) would be required. (Not a v1 target; user is on macOS.)

---

## 4. Wire protocol (SysEx)

### Frame

```
F0  7D  <direction>  <ascii-json-payload...>  F7
```

- `F0` / `F7` — SysEx start / end (MIDI standard).
- `7D` — the SysEx manufacturer ID reserved for **non-commercial / educational** use. Safe, no registration.
- `<direction>` — `0x01` = request (server → FL), `0x02` = response (FL → server).
- `<ascii-json-payload>` — the command/result as **ASCII JSON**.

**Why ASCII JSON?** Every byte between `F0` and `F7` must be 7-bit (`0x00`–`0x7F`). `json.dumps(obj)` with the
default `ensure_ascii=True` emits only ASCII bytes (non-ASCII becomes `\uXXXX` escapes), so the JSON string drops
straight into the SysEx payload with no extra encoding layer. Simple and robust.

### Request payload

```json
{ "id": 42, "cmd": "set_grid_bit", "args": { "channel": 0, "step": 4, "value": 1 } }
```

- `id` — monotonically increasing integer, used to correlate the reply.
- `cmd` — a Fruitful command name (see §5). Higher-level than raw API calls where useful.
- `args` — named arguments.

### Response payload

```json
{ "id": 42, "ok": true, "result": null }
```

or on failure:

```json
{ "id": 42, "ok": false, "error": "channel index 99 out of range" }
```

### Correlation & timeouts

The client sends a request and blocks until a Response frame with the matching `id` arrives, or a timeout
(default 5 s) elapses. FL processes the command on its own event loop, so replies are near-immediate but the
timeout guards against a missing/uninstalled device script.

### Chunking (future)

A single SysEx message can be large, but very large payloads (e.g. full project-state dumps) may need chunking.
v1 keeps payloads small; chunking is a documented future extension (add `seq`/`total` fields to the frame).

---

## 5. Command set (v1)

Commands map to verified native API functions (see NOTES.md for the API audit).

| `cmd` | Args | FL API used | Notes |
| --- | --- | --- | --- |
| `ping` | — | — | Health check / round-trip test. Returns `"pong"` + FL version. |
| `get_channel_count` | — | `channels.channelCount` | Round-trip sanity read. |
| `set_grid_bit` | channel, step, value | `channels.setGridBit` | Single step on/off. |
| `program_pattern` | channel, steps[] | `channels.setGridBit` ×N | Write a whole 16/32-step row. |
| `set_channel_volume` | channel, value (0–1) | `channels.setChannelVolume` | |
| `set_channel_pan` | channel, value (−1..1) | `channels.setChannelPan` | |
| `set_channel_name` | channel, name | `channels.setChannelName` | |
| `route_channel_to_mixer` | channel, track | `channels.setTargetFxTrack` | |
| `set_plugin_param` | index, param, value, slot? | `plugins.setParamValue` | Normalized value; slot is `-1` for a Channel Rack generator. |
| `get_plugin_params` | index, slot? | `plugins.getParamName`/`getParamCount` | Returns names and current values for Claude to learn a plugin's knobs. |
| `transport` | action (play/stop/record) | `transport.start`/`stop`/`record` | |
| `get_project_state` | — | `channels`/`mixer` read APIs | Channels + mixer summary for context. |

The MCP **tool** surface (what Claude sees) wraps these — e.g. a `program_drum_pattern` tool may accept a
human-friendly grid and expand to several `program_pattern` commands.

---

## 6. Milestones

- **M1 — The bridge (validated).** SysEx transport both directions. Prove `ping` and `set_grid_bit` round-trip on
  real hardware. Deliverables: `protocol.py`, `bridge.py`, minimal `device_Fruitful.py`, a `ping` MCP tool.
- **M2 — Drum programming (validated).** Full step-sequencer command set + a friendly `program_drum_pattern` MCP tool.
- **M3 — Channel & mixer control (validated).** Volume/pan/name/color/routing,
  gain-staging helpers.
- **M4 — Plugin parameters & project awareness (validated).** Inspect/set plugin
  parameters by index and read `get_project_state` context snapshots.
- **M5 — Packaging & onboarding.** `fruitful install` helper, IAC setup docs, Claude Desktop config.

---

## 7. Open items to verify on real hardware

Validated against FL Studio MIDI scripting version 45 on macOS:

1. **Inbound SysEx callback** — `OnMidiIn` receives SysEx payloads; `OnSysEx` is a guarded fallback because
   it may receive an event with no payload.
2. **`json` availability** — confirmed.
3. **SysEx round trip** — confirmed with the IAC Driver over one duplex Request port.
4. **Outbound SysEx** — confirmed on the device script's linked Request port.

Still open:

1. **Tempo/BPM** — use `mixer.setCurrentTempo` where supported; validate when transport expansion begins.
