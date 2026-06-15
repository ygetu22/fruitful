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
                                          (virtual MIDI ports: Request / Response)
```

Commands travel as **SysEx** messages, whose payload is an arbitrary-length byte stream, so Fruitful sends
structured commands and receives real return values. See [`SPEC.md`](./SPEC.md) for the full design.

## Status

🚧 **In active development** (started 2026, ongoing). The architecture and the core MIDI/SysEx bridge are
designed and implemented; command coverage is expanding milestone by milestone (see the roadmap in
[`SPEC.md`](./SPEC.md)). The full source will be published here as the project matures.

## License

To be determined before the full source release.
