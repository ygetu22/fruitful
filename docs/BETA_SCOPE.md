# Development and release status

## Release goal

A macOS FL Studio user can follow the README, connect their AI client, and create a checked house beat using
three loaded drum channels.

## Implemented

- Guided setup, packaged FL scripts, overwrite protection, and a connection doctor.
- Drum steps, channel volume/pan/name/routing, plugin parameters, project state, tempo, and transport.
- House Starter with drum/tempo readback and an explicit error if the result cannot be confirmed.
- Optional genre plans, Freesound search, and experimental Piano Roll writing.

MIDI commands run one at a time. Lost connections close their ports; later calls can reopen them. Commands
are never retried automatically because a timed-out write may already have changed the project.

## Checks

Onboarding, MIDI failure handling, command validation, beat readback, and sound-search behavior have automated
coverage. Tests use temporary files and fake FL/provider responses. A real MCP client also checks startup and
local planning tools. See [verification notes](ONBOARDING_VERIFICATION.md).

## Before a stable release

- Complete the live FL walkthrough and check the supported FL version. Live testing is deferred at Yakob's request.
- Check the README on a second machine and in the intended AI client.
- Verify real Freesound access and the generated Piano Roll script separately.
- Finish the release checks and record a real demonstration.

The code and packaged FL scripts use the MIT license included in the repository.

## Limits

Fruitful edits the current pattern and loaded instruments. It does not load instruments/samples, arrange/export
finished songs, or provide automatic rollback. A failed multi-step operation can leave partial changes.
Windows/Linux support and mixer gain/name editing are outside this release. Piano Roll remains experimental.

## Developer commands

```bash
.venv/bin/python -m unittest discover -s tests -v
uv build
uvx ruff check src tests device 'pianoroll/Fruitful Apply.pyscript'
uvx ruff format --check src tests device 'pianoroll/Fruitful Apply.pyscript'
```

[Protocol and design](../SPEC.md) · [Development history](../NOTES.md)
