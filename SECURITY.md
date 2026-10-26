# Security

Fruitful is a macOS beta. The latest scripts still need live FL Studio verification. Use a scratch project or
save a copy before editing; failed operations can leave partial changes.

## What runs locally

The MCP server uses stdio and talks to FL Studio over virtual MIDI ports. It accepts a fixed set of commands,
not arbitrary code. Other local processes with access to those MIDI ports can still send commands.

The experimental Piano Roll tools use local request files and a macOS keyboard shortcut. They depend on the
correct window being focused. Run one Piano Roll client at a time.

## What can leave your computer

- Your AI client may send project details to its model provider. Check that client's settings.
- Optional Freesound search sends your search terms and configured API key to Freesound over HTTPS.

Fruitful keeps the Freesound key in an authorization header, not request URLs. Cached sound metadata stays in
the configured local SQLite database. Don't include keys or private project details in bug reports.

## Releases

This repository contains source code. No package-registry release or automated release pipeline is configured.
The Python dependencies use version constraints; the full dependency tree is not locked. Don't assume builds
are pinned or have signed provenance.

## Report a problem

Use the repository's **Security → Report a vulnerability** option if available. Otherwise, contact the maintainer
privately through their GitHub profile. Avoid public issues containing exploit details, credentials, or private files.
Include the Fruitful and FL Studio versions, what happened, and steps to reproduce.
