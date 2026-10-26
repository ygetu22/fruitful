# Optional features

The basic setup does not need these.

## Piano Roll — experimental

Read, add, or replace notes in the **currently open** Piano Roll. This uses a keyboard shortcut and depends on
window focus. Use a scratch project; replace mode clears existing notes.

1. Install the extra script, using your actual FL Settings folder:

   ```bash
   .venv/bin/fruitful install-scripts --settings-dir "/your/FL Studio/Settings" --piano-roll
   ```

2. In your MCP client's Fruitful environment, set `FRUITFUL_PIANO_ROLL_DIR` to the `Piano roll scripts` folder
   printed by the installer.
3. Allow your MCP client to control FL in macOS Accessibility/Automation settings.
4. Open the intended Piano Roll. Run **Fruitful Apply** from its scripts menu once so FL remembers it for
   Command-Option-Y. Reload FL's script after installation if needed.
5. Ask Fruitful to read the notes before writing any.

The installer generates the path; don't copy the source template directly. Moving the scripts folder requires
reinstalling and updating the environment value. `FRUITFUL_FL_APP` and `FRUITFUL_FL_PROCESS` override the app/process
names if they differ from `FL Studio` and `OsxFL` on your installation.

## Sound search

Set `FREESOUND_API_TOKEN` in your MCP client's Fruitful environment using your own
[Freesound API key](https://freesound.org/apiv2/apply/). Ask for CC0 sounds by name or role.

Results contain metadata and preview links. Fruitful does not download or load samples into FL Studio.
Metadata is cached for seven days in `~/.fruitful/library.sqlite3`. `FRUITFUL_LIBRARY_DB` changes that location.
Real provider access still needs verification before release.

## Genre planning

Ask for a genre starter plan. Fruitful includes hip-hop, rage trap, R&B, reggae, Afrobeat, Latin, jazz, and rock.
These are editable suggestions for tempo, sound roles, and arrangement; they don't change your project.
Only the House Starter currently applies a prepared drum template.

## Updating scripts

Reinstall the Python package after changing source, then run setup again. If an installed script differs,
Fruitful leaves it alone. Back it up before replacing it with:

```bash
.venv/bin/fruitful install-scripts --settings-dir "/your/FL Studio/Settings" --force
```

Add `--piano-roll` to also update that experiment. Add `--dry-run` to preview destinations without writing.
