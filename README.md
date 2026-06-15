# 🍊 Fruitful

> Your AI co-producer for FL Studio.

Most people who want to make music never get the sound out of their head — not because they're short on ideas,
but because the theory and a DAW full of menus get in the way first. Fruitful is about tearing that wall down:
say what you're hearing in plain words, and it helps you build it in FL Studio.

**Fruitful** is an open-source [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that
connects the Claude desktop app to **FL Studio**. It's meant to be a real co-pilot — approachable enough for
someone opening a DAW for the first time, and quick enough to stay useful once you already know your way around.

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

## Why a separate project?

A few open-source projects already connect AI to FL Studio, and they're worth a look — especially
[Flapi](https://github.com/MaddyGuthridge/Flapi), which paved the way for talking to FL's scripting API
remotely.

Fruitful exists because it takes a different path. Most existing tools record notes into FL through a virtual
MIDI port; Fruitful instead drives FL's native scripting API directly with structured commands, focusing on
reliability and on the parts of the API those tools don't cover. That's a different foundation rather than a
tweak on top of an existing one, so it made more sense to build it cleanly than to bolt it onto a project
designed around another approach.

## Status

🚧 **In active development** (started 2026, ongoing). The architecture and the core MIDI/SysEx bridge are
designed and implemented; command coverage is expanding milestone by milestone (see the roadmap in
[`SPEC.md`](./SPEC.md)). The full source will be published here as the project matures.

## License

Released under the [MIT License](./LICENSE) — free to use, modify, and build on.
