# 🍊 Fruitful

> Your AI co-producer for FL Studio.

**Fruitful** is an open-source [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that
connects the Claude desktop app to **FL Studio**, letting you produce music with natural-language prompts.

The mission: lower the entry barrier to music production — the theory and the DAW learning curve — and act as a
genuine co-pilot for advanced producers.

## Design philosophy

Fruitful is built around FL Studio's **native MIDI Controller Scripting API**, using only directly supported
operations so that every action is deterministic and reliable. Rather than emulating note input, it issues
structured commands and reads project state, giving Claude accurate context to work from.

This keeps the v1 surface focused on what the API supports well today:

| Capability | How |
| --- | --- |
| 🥁 Drum / beat programming | Writes step-sequencer patterns directly (`channels.setGridBit`) |
| 🎚️ Channel control | Volume, pan, name, color, pitch, mute/solo, route to mixer track |
| 🎛️ Plugin parameter control | Tune *any* native or third-party VST knob **by name** (`plugins.setParamValue`) |
| 🎚️ Mixer control | Gain staging, routing, naming |
| ▶️ Transport | Play / stop / record / loop / position |
| 🧠 Project awareness | Reads your actual rack, mixer, and plugins so Claude acts on context |

Piano-roll note authoring is intentionally out of scope for v1: FL's API does not expose a native, persistent
note-writing function. See [`SPEC.md`](./SPEC.md) for the rationale.

## How it works

```
Claude Desktop ──MCP──▶ Fruitful server (FastMCP) ──SysEx──▶ FL Studio device script ──▶ FL Studio engine
                                          (one duplex virtual MIDI port)
```

Commands travel as **SysEx** messages, whose payload is an arbitrary-length byte stream, so Fruitful sends
structured commands and receives real return values. See [`SPEC.md`](./SPEC.md) for the full design.

## Status

🚧 Early development. The bridge, drum programming, channel controls, transport, and first project-awareness tools are validated in FL Studio; command coverage is still expanding.
Private for now — will be made public later.

## Project layout

See [`NOTES.md`](./NOTES.md) for a living, file-by-file guide and the decision log.

## License

TBD (will be set before going public).
