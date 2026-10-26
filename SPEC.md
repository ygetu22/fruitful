# Architecture and protocol

Fruitful is a local stdio MCP server. It forwards commands to an FL Studio device script over a virtual MIDI
bus. The core tools use FL's controller scripting APIs; optional Piano Roll writing uses a separate file/shortcut
bridge. Public feature scope lives in [BETA_SCOPE.md](docs/BETA_SCOPE.md).

## Components

```text
MCP client ↔ Fruitful server ↔ MIDI/SysEx ↔ FL device script ↔ FL Studio
```

- `server.py` owns tool definitions and multi-step workflows.
- `bridge.py` owns MIDI ports, request IDs, timeouts, and cleanup.
- `device_Fruitful.py` runs in FL and dispatches validated commands to native APIs.
- One duplex IAC bus, **Fruitful Request**, carries both directions. FL's linked device output sends replies
  back over that bus. Windows/Linux configuration is outside this beta.

The MIDI approach was informed by [Flapi](https://github.com/MaddyGuthridge/Flapi). Fruitful implements its own
command bridge.

## SysEx frame

```text
F0 7D <direction> <ASCII JSON> F7
```

- F0/F7 frame the message. Mido handles them outside the payload.
- 7D is the non-commercial/educational SysEx manufacturer ID used by this implementation.
- Direction 01 means request; 02 means response.
- JSON uses ASCII escapes so each payload byte stays within MIDI's 7-bit range. Outgoing requests reject
  nonfinite numbers. The device script mirrors the protocol constants because it cannot import this package.

Request:

```json
{"id": 42, "cmd": "set_grid_bit", "args": {"channel": 0, "step": 4, "value": 1}}
```

Response:

```json
{"id": 42, "ok": true, "result": null}
```

Failure:

```json
{"id": 42, "ok": false, "error": "Channel no longer exists."}
```

Request IDs increase from a random starting value per bridge, so separate local clients do not normally reuse
IDs. Replies must match a pending ID. Malformed, unrelated, and duplicate replies are ignored.

## Failure behavior

Each bridge serializes requests. The default reply timeout is five seconds. Failed sends and timeouts remove
pending requests and close ports; a later call can reopen them. Writes are never retried automatically because
FL may already have applied a command whose reply was lost.

MIDI calls are serialized per request, not across a whole workflow or across processes. Don't edit the target
pattern or run competing write clients during House Starter. It checks each written drum row and the applied
tempo before success. Errors report confirmed rows; there is no automatic rollback.

## Device commands

These are the implemented dispatch commands. Earlier live sessions exercised the original versions;
regression tests simulate FL responses. The revised scripts still need the deferred live walkthrough.

| `cmd` | Args | FL API used | Notes |
| --- | --- | --- | --- |
| `ping` | — | — | Health check / round-trip test. Returns `"pong"` + FL version. |
| `get_channel_count` | — | `channels.channelCount` | Round-trip sanity read. |
| `set_grid_bit` | channel, step, value | `channels.setGridBit` | Single step on/off. |
| `program_pattern` | channel, steps[] | `channels.setGridBit` ×N | Write a whole 16/32-step row. |
| `get_pattern` | channel, length? | `channels.getGridBit` ×N | Read a step row as booleans; default 16 steps. |
| `set_channel_volume` | channel, value (0–1) | `channels.setChannelVolume` | |
| `set_channel_pan` | channel, value (−1..1) | `channels.setChannelPan` | |
| `set_channel_name` | channel, name | `channels.setChannelName` | |
| `route_channel_to_mixer` | channel, track | `channels.setTargetFxTrack` | |
| `set_plugin_param` | index, param, value, slot? | `plugins.setParamValue` | Normalized value; slot is `-1` for a Channel Rack generator. |
| `get_plugin_params` | index, slot? | `plugins.getParamName`/`getParamCount` | Returns names and current values for Claude to learn a plugin's knobs. |
| `get_plugin_param_page` | index, start?, limit?, slot? | `plugins.getParamName`/`getParamCount` | Bounded page (maximum 64) for large plugin parameter surfaces. |
| `get_tempo` | — | `mixer.getCurrentTempo` | Returns the current project tempo in BPM (Fruitful normalizes FL's internal 1,000x value). |
| `set_tempo` | bpm | `mixer.setCurrentTempo` | Sets and returns BPM; Fruitful converts to/from FL's internal 1,000x value. |
| `transport` | action (play/stop/record) | `transport.start`/`stop`/`record` | |
| `get_project_state` | — | `channels`/`mixer` read APIs | Channels + mixer summary for context. |


MCP tool names may differ: `program_drum_pattern` wraps `program_pattern`, and `get_drum_pattern` wraps
`get_pattern`. The MCP `get_plugin_params` tool fetches multiple bounded pages; the direct device command of
that name returns at most one 64-entry page. Prefer `get_plugin_param_page` for large instruments.

## Experimental Piano Roll bridge

The installer generates the script's directory. The server writes a request with a UUID to that directory,
then triggers FL's remembered Piano Roll script. FL consumes the request before editing and prepares all notes
before a replace operation clears the existing score. This prevents simple replay and invalid-input clearing;
it does not guarantee rollback if FL fails while applying notes.

The server waits for a matching response UUID. This workflow requires the correct Piano Roll to be focused,
the configured shortcut, and macOS permissions. Use one Piano Roll client at a time; the request files are
shared. Keep it experimental until the generated script is verified in FL.

## Verification

See [ONBOARDING_VERIFICATION.md](docs/ONBOARDING_VERIFICATION.md) for current checks and limits. Earlier September
sessions confirmed SysEx round trips, the linked output bus, and FL's tempo scaling (BPM × 1,000 at the native
API boundary). Those sessions do not certify later changes or additional platforms.
