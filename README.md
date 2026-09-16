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
| 🥁 Drum / beat programming | Reads and writes step-sequencer patterns directly (`channels.getGridBit` / `setGridBit`) |
| 🎚️ Channel control | Volume, pan, name, color, pitch, mute/solo, route to mixer track |
| 🎛️ Plugin parameter control | Inspect and tune native or third-party plugin parameters by index (`plugins.setParamValue`) |
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

🚧 Early development. The bridge, drum programming, channel controls, transport, and first project-awareness tools are validated in FL Studio and reachable from Codex CLI; command coverage is still expanding.
Private for now — will be made public later.

## Setup

Fruitful currently targets macOS and FL Studio MIDI scripting version 45.

1. In macOS **Audio MIDI Setup** > **MIDI Studio**, enable the IAC Driver and create a port named
   `Fruitful Request`.
2. Install the device script at
   `.../FL Studio/Settings/Hardware/Fruitful/device_Fruitful.py`.
3. In FL Studio **Options** > **MIDI Settings**, enable `Fruitful Request` as both input and output. Set the
   input controller type to `Fruitful` and give both entries the same FL port number.
4. From this repository, create a Python 3.12 virtual environment and install the package with
   [`uv`](https://docs.astral.sh/uv/):

   ```bash
   uv venv --python 3.12
   uv pip install -e .
   ```

5. With FL Studio open, verify the connection:

   ```bash
   .venv/bin/fruitful doctor
   ```

   A successful check reports the FL Studio MIDI scripting version.

### Codex CLI

Fruitful is a local stdio MCP server, so it works with compatible terminal clients. Add it to Codex CLI with:

```bash
codex mcp add fruitful -- /Users/yakob/projects/fruitful/.venv/bin/fruitful
```

Confirm it is registered with `codex mcp list`, then start `codex` in a terminal and ask it to use Fruitful's
`ping` tool. Keep FL Studio open while using the server.

Other MCP-compatible clients can launch the same `fruitful` command; Fruitful does not depend on Claude Desktop.

## Project layout

See [`NOTES.md`](./NOTES.md) for a living, file-by-file guide and the decision log.

## License

TBD (will be set before going public).
