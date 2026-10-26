# Developer notes

## Code map

| File | Responsibility |
| --- | --- |
| `src/fruitful/cli.py` | Setup, connection checks, and MCP startup |
| `src/fruitful/setup.py` | Packaged scripts, installation paths, and overwrite protection |
| `src/fruitful/server.py` | MCP tools and the checked House Starter workflow |
| `src/fruitful/bridge.py` | MIDI connection, request correlation, timeouts, and cleanup |
| `src/fruitful/protocol.py` | SysEx encoding and decoding |
| `src/fruitful/validation.py` | Check command arguments before sending MIDI |
| `device/device_Fruitful.py` | Dispatch commands inside FL Studio |
| `src/fruitful/pianoroll.py` | Experimental file/shortcut bridge |
| `pianoroll/Fruitful Apply.pyscript` | Experimental FL-side note operations |
| `src/fruitful/styles.py` | Local genre planning data |
| `src/fruitful/sounds.py` | Optional Freesound search and metadata cache |
| `tests/` | Setup, protocol client, and simulated MIDI/FL/provider checks |

## Decisions to preserve

- One duplex IAC bus carries requests and replies. A separate response bus was tried and did not work with FL's
  linked device output. Keep the SysEx direction byte to distinguish traffic.
- The device script cannot import the installed Fruitful package. Keep its protocol constants aligned with
  protocol.py. Use FL's controller APIs for the core tools; Piano Roll uses a separate experiment.
- MIDI requests run one at a time. Never retry writes automatically: timeout does not mean a change failed.
- House Starter uses loaded, named drum channels and the current pattern. It checks written rows and tempo.
  It does not load instruments, select a pattern, or roll back partial changes.
- Large plugin parameter lists use pages of at most 64 entries. Surge XT exposed thousands of parameters in
  earlier sessions, so a single unbounded SysEx response is unsuitable.
- FL Piano Roll scripts did not expose `__file__` in the tested setup. The installer generates an explicit
  directory in the script; the client environment must point to that same directory.
- The Piano Roll request is consumed before editing, and replacement notes are prepared before clearing old
  notes. Window focus and the remembered keyboard shortcut still need live verification.
- Freesound is opt-in. Keep the API key in the authorization header, preserve returned license metadata, and
  return only CC0 results. The cache is optional; a cache error must not prevent a successful online search.

## Verification history

- June 2026: protocol and initial bridge implementation.
- September 16–18, 2026: live macOS sessions checked MIDI round trips, drums, channel controls, tempo,
  plugin parameters, House Starter, and experimental Piano Roll note read/write. These checks predate the
  current cleanup and do not certify the revised scripts.
- October 26, 2026: portable onboarding, concise guides, and regression coverage. Further live FL testing is
  deferred at the user's request. Current evidence and remaining checks are in the documents below.

[Release scope](docs/BETA_SCOPE.md) · [Verification](docs/ONBOARDING_VERIFICATION.md) · [Protocol](SPEC.md)

## Provider references

- [Freesound search](https://freesound.org/docs/api/resources_apiv2.html)
- [Freesound authentication](https://freesound.org/docs/api/authentication.html)
- [FL tempo controls](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/toolbar_panels.htm)
