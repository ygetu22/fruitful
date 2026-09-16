# Fruitful — Project Notes (living doc)

This is the living guide to the repo: what each file is, the decisions behind them, how to set
things up, and a session-by-session log. Update it whenever files change. Companion to the
high-level [`README.md`](./README.md) and the design [`SPEC.md`](./SPEC.md).

---

## File-by-file guide

```
fruitful/
├── README.md                     Public-facing overview, design philosophy, capability table.
├── SPEC.md                       Technical spec: architecture, SysEx protocol, command set, milestones.
├── NOTES.md                      ← you are here. Living file guide + decision log + session log.
├── pyproject.toml                Package metadata + deps (fastmcp, mido, python-rtmidi). `fruitful` CLI entry.
├── .gitignore                    Ignores venvs, caches, .DS_Store, .env.
│
├── src/fruitful/                 The MCP server side (a normal Python process).
│   ├── __init__.py               Package marker + version + one-line purpose.
│   ├── protocol.py               SOURCE OF TRUTH for the SysEx wire format. encode()/decode().
│   ├── bridge.py                 Bridge client: opens virtual MIDI ports, sends/receives SysEx,
│   │                             correlates request/response by `id`, with timeout.
│   └── server.py                 FastMCP server. Defines the tools Claude sees; forwards to the bridge.
│
└── device/
    └── device_Fruitful.py        The FL Studio device script — runs INSIDE FL's sandbox. Receives
                                   SysEx, calls FL's native API, sends results back. Mirrors protocol.py.
```

### Key design notes per component

- **`protocol.py`** — Frame is `F0 7D <dir> <ascii-json> F7`. `7D` is the SysEx ID reserved for
  non-commercial/educational use. ASCII JSON keeps every payload byte 7-bit (a hard SysEx
  requirement) with zero extra encoding. This file is the protocol's source of truth.
- **`device_Fruitful.py`** — Cannot import our package (FL sandbox), so it **re-implements** the
  protocol inline using only stdlib `json`. **If you change `protocol.py`, change this too.** It
  never crashes the script: any command error is caught and returned as `{"ok": false, "error": ...}`.
- **`bridge.py`** — Matches port names by substring (MIDI backends decorate names). Uses one duplex
  `Fruitful Request` port because FL sends to a device script's linked output. Receives on a
  background callback thread; `call()` blocks on a per-request queue until the matching `id` replies.
- **`server.py`** — One shared `Bridge`, opened lazily so the server starts even before FL is up.
  Exposes bridge health, step programming, channel/mixer control, plugin inspection, project state,
  and transport tools. `fruitful doctor` performs a direct bridge health check outside MCP.

---

## Decision log

- **Name: `Fruitful`** — nods to FL Studio's "FruityLoops" origin + means productive/generative.
  Confirmed free on PyPI.
- **Scope: native, directly-supported API only.** No piano-roll melody writing in v1: FL's API has
  no native persistent note-write function. Priority is reliable, deterministic operations across the
  full natively-supported surface (drums, channel/mixer control, plugin params, project state).
- **Transport: a focused SysEx bridge** over two virtual MIDI ports (Request/Response). Chosen over
  file-based IPC with a keyboard-shortcut trigger (depends on window focus, adds latency) and TCP
  sockets inside the script (not reliably supported by the sandbox). Prior art: Flapi (credited),
  which is unmaintained, so Fruitful implements its own focused bridge.
- **Protocol: ASCII-JSON-in-SysEx** — structured commands + return values, avoiding the 7-bit value
  limit of standard MIDI note messages.

---

## Setup & testing (manual — needs FL Studio)

M1-M4 are validated against FL Studio's MIDI scripting version 45. Keep regression-testing on the real
machine as the command surface expands; FL itself cannot run in CI.

1. **Create a virtual MIDI port (macOS):** Open *Audio MIDI Setup* → *MIDI Studio* → double-click
   *IAC Driver* → enable "Device is online" → name a port **`Fruitful Request`**.
2. **Install the device script:** copy `device/device_Fruitful.py` into a subfolder under FL's
   hardware scripts dir (e.g. `.../FL Studio/Settings/Hardware/Fruitful/`).
3. **Configure FL:** Options → MIDI Settings → enable `Fruitful Request` as both input and output, assign
   the input controller type to "Fruitful", and use the same FL port number for both entries.
4. **Install the server:** `pip install -e .` (ideally in a venv).
5. **Smoke test:** run a quick `Bridge().call("ping")` and expect `{"pong": true, "fl_version": ...}`.
6. **Wire to an MCP client:** add Fruitful as an MCP server (`fruitful` command). Codex CLI is the first
   terminal client covered in M5.

### Hardware verification results
1. `OnMidiIn` receives SysEx payloads on FL Studio MIDI scripting version 45; `OnSysEx` can receive an event
   with `sysex` set to `None`, so it remains a guarded fallback.
2. `json` is available in FL's sandbox.
3. SysEx request/response works over the macOS IAC Driver using one duplex `Fruitful Request` port.
4. `device.midiOutSysex` returns on the linked Request port. The protocol direction byte separates commands
   from replies.

---

## Session log

- **2026-09-16** — Validated M1-M4 against FL Studio MIDI scripting version 45.
  - Verified bridge ping, channel count, compact project state, plugin parameter inspection, and plugin writes.
  - Verified step write/clear, channel volume/pan/name/routing writes, and play/stop transport.
  - Corrected the bridge to use one duplex `Fruitful Request` IAC port: FL sends device-script output to the
    script's linked port, so the separate Response bus could not receive replies.

- **2026-09-16** — Started M5 onboarding with a `fruitful doctor` connection check and macOS/Codex CLI
  setup instructions.

- **2026-09-16** — Validated the terminal workflow end to end: Codex CLI launched Fruitful through MCP and
  successfully called `ping` against FL Studio MIDI scripting version 45. No project files were changed.
  - Codex also read the current Channel Rack/mixer state and set channel 0 pan to `-0.25`, then restored it
    to `0.0`.
  - Codex programmed and FL Studio played a one-bar trap drum pattern: kick on steps 0/3/8/11, clap on 4/12,
    and hi-hats on every even step (channels 0, 1, and 2 respectively).
  - After reloading the device script, `get_pattern` read back each row exactly. Read-only step-pattern state is
    now hardware-validated.
  - M5 onboarding changes are locally complete and uncommitted; do not commit or push until the user asks.

- **2026-09-16** — Added the first M4 slice: plugin parameter inspection/editing and compact project-state
  snapshots for Channel Rack channels and mixer tracks.

- **2026-09-15** — Installed the device script at
  `/Volumes/LaCie/FLStudioData/FL Studio/Settings/Hardware/Fruitful/device_Fruitful.py`.
  - Local syntax compilation and SysEx protocol round-trip pass.
  - Awaiting IAC virtual-port and FL Studio MIDI configuration for the hardware smoke test.
- **2026-09-15** — Added MCP/device commands for channel volume, pan, rename, mixer routing, and
  play/stop/record transport control.
- **2026-06-14** — Research → decisions → first code.
  - Resolved feasibility (native API audit), locked name/scope/architecture.
  - Wrote README, SPEC, NOTES; scaffolded package + FL device script.
  - **Milestone 1 code complete & locally verified** (syntax compiles; protocol round-trip + 7-bit
    safety tested). Not yet tested against FL Studio.
  - Initial commit `e2b8921` (local; not pushed to a remote yet).
