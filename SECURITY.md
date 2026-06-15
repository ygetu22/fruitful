# Security

Fruitful is in active development. This document explains how it's designed to stay safe,
and how to report a problem if you find one.

## Security model

Fruitful is a **local tool**. The MCP server runs on your own machine and talks to FL Studio
over **local virtual MIDI ports** — there is no website, no remote server, no accounts, and no
user data leaving your computer. There is no network-facing surface to attack.

Two design choices keep the runtime safe:

- **Fixed command set, not arbitrary execution.** The FL Studio side accepts only a known list
  of commands (e.g. set a step, set a parameter), dispatched by name. It does not expose a way to
  run arbitrary code or arbitrary API calls. This is a deliberate trade-off: a smaller, predictable
  surface in exchange for less flexibility.
- **Defensive command handling.** Incoming messages are validated before anything runs, and a bad
  or malformed message is ignored rather than allowed to crash FL Studio.

Because the bridge is local-only, abusing it would require code already running on your machine —
at which point the DAW is not the thing at risk.

## Supply chain and releases

For a tool meant to be installed by others, the most important thing to protect is the path from
source code to the package people download. When Fruitful is published, releases follow these rules:

- **Trusted Publishing (OIDC)** for any package registry — no long-lived API tokens stored as secrets.
- **Pinned versions** for all CI/build actions, so a compromised dependency or action can't slip code
  into a release.
- **Least-privilege CI permissions**, and **no build caches** in the release pipeline (to avoid cache
  poisoning).
- **Dependabot enabled** for dependency security updates.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Instead, use GitHub's private vulnerability reporting on this repository
(the **Security** tab → **Report a vulnerability**). That keeps the details private until there's a fix.

Since the project is early, please include clear steps to reproduce. Thanks for helping keep it safe.
