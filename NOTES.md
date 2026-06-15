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
- **`bridge.py`** — Matches port names by substring (MIDI backends decorate names). Receives on a
  background callback thread; `call()` blocks on a per-request queue until the matching `id` replies.
- **`server.py`** — One shared `Bridge`, opened lazily so the server starts even before FL is up.

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

The code is complete for Milestone 1 but **must be tested on the real machine** (FL can't run in CI).

1. **Create virtual MIDI ports (macOS):** Open *Audio MIDI Setup* → *MIDI Studio* → double-click
   *IAC Driver* → enable "Device is online" → add two ports named **`Fruitful Request`** and
   **`Fruitful Response`**.
2. **Install the device script:** copy `device/device_Fruitful.py` into a subfolder under FL's
   hardware scripts dir (e.g. `.../FL Studio/Settings/Hardware/Fruitful/`).
3. **Configure FL:** Options → MIDI Settings → set the `Fruitful Request` input's controller type to
   "Fruitful", enable input; enable `Fruitful Response` as an output.
4. **Install the server:** `pip install -e .` (ideally in a venv).
5. **Smoke test:** run a quick `Bridge().call("ping")` and expect `{"pong": true, "fl_version": ...}`.
6. **Wire to Claude Desktop:** add Fruitful as an MCP server (`fruitful` command) — covered in M5.

### Open items to verify on hardware (see SPEC.md §7)
1. Exact inbound-SysEx callback name (`OnSysEx` vs `OnMidiMsg`+`event.sysex`).
2. `json` availability in FL's sandboxed interpreter (expected yes).
3. SysEx round-trip latency/reliability over the IAC Driver.
4. Outbound `device.midiOutSysex` sends on the intended Response port.

---

## Session log

- **2026-06-14** — Research → decisions → first code.
  - Resolved feasibility (native API audit), locked name/scope/architecture.
  - Wrote README, SPEC, NOTES; scaffolded package + FL device script.
  - **Milestone 1 code complete & locally verified** (syntax compiles; protocol round-trip + 7-bit
    safety tested). Not yet tested against FL Studio. Not yet committed (awaiting go-ahead).
