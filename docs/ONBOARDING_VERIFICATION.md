# Onboarding verification — October 26, 2026

## Results

All 52 checks passed in the working environment and fresh wheel/source installations after the final cleanup.
The isolated runs used the tests extracted from the rebuilt source archive, outside the development checkout.

- Existing development environment: Python 3.12.13, FastMCP 3.4.2.
- Fresh wheel installation: Python 3.12.13, FastMCP 3.4.11.
- Fresh source archive installation: Python 3.12.13, FastMCP 3.4.11.

Fresh environments were outside the checkout in temporary directories, with independently installed dependencies.
The source archive built into a wheel during installation. Both installations provided the packaged FL scripts.
This verifies isolation from the development checkout, not compatibility with a second physical machine.

## Coverage

- An existing Settings folder is required; installer paths include spaces and Ge'ez characters.
- Preview creates no files; repeat installation leaves matching files untouched.
- Conflicts are checked before writes; explicit force replaces them; destination-file symlinks are refused.
- Piano Roll path generation produces valid Python with the selected, resolved directory.
- Doctor missing-script, missing-IAC, unavailable-backend, unexpected-reply, timeout, success, and offline behavior.
  MIDI and FL responses in these automated doctor tests are mocked.
- Installed CLI help/version, subcommand help, invalid command handling, and actual script installation into
  temporary Settings folders, including overwrite refusal and force replacement.
- A real MCP stdio client launches the installed executable with no arguments, initializes, lists tools, and
  calls list_genre_starters. No language model or FL write operation is involved.
- Guided setup prints the installed command and installs only the core FL script.
- Fake MIDI covers duplicate/malformed replies, simultaneous callers, failed sends, timeouts, and reconnection.
- FL-side validation is exercised with fake FL modules before any write.
- The House Starter must read back matching drum rows and tempo before reporting success. Mocked failures stop
  playback and name confirmed rows; missing/ambiguous drum roles produce no writes.
- Mocked Freesound checks cover CC0 filtering, secret-free errors, short/long cached queries, and unavailable cache.
- Cleanup regressions cover consumed Piano Roll requests, invalid replacements preserving existing notes,
  failed-trigger cleanup, malformed responses/provider data, shared style-data isolation, and request IDs
  initialized separately for each bridge.

An early integration assertion was corrected to compare resolved paths: macOS maps /var to /private/var.
The generated path was valid; the test had compared the symlink alias as literal text.

## Reproduce

From the checkout, build distributions with `uv build --out-dir /private/tmp/fruitful-beta-artifacts`. Create
separate Python 3.12 environments with `uv venv --python 3.12 <temporary-environment>`, then use
`uv pip install --python <temporary-environment>/bin/python <wheel-or-source-archive>`.

From a directory outside the checkout, run:

```text
<temporary-environment>/bin/python -m unittest discover -s <checkout>/tests -v
```

The source distribution includes tests; the wheel contains the application and FL script assets.

## Actual FL connection check

The following check predates the latest reliability changes. Further live testing is deferred at Yakob's request.

`fruitful doctor --offline` found Fruitful Request in both MIDI input/output lists. A real read-only ping timed
out after five seconds and exited 1 with setup instructions. FL Studio was closed and its configured external
user-data volume was unavailable. No installed FL scripts, projects, or client settings were changed.

## Still required

With the user's FL setup available, check connected doctor, controller misconfiguration, project-state reads,
and the README's first beat on an explicitly chosen scratch project. Revalidate the generated Piano Roll
script separately before recommending the experiment. Verify optional Freesound discovery separately.

Lint/import checks and formatting checks passed. Both distributions built successfully and included the FL
scripts and license. A pattern scan of the 27 candidate repository files found no credential patterns or local
home-directory paths; no environment files, caches, build output, or local databases were among those candidates.
This was a source/package review, not a provider-side credential audit or a live FL verification.
