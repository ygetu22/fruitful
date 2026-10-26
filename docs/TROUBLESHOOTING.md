# If something doesn't work

| Problem | Try this |
| --- | --- |
| No Fruitful MIDI port | Enable IAC Driver and create a bus named Fruitful Request. |
| FL doesn't answer | Keep FL open. Enable the bus as input/output, select Fruitful as controller, and give both the same port number. |
| Fruitful isn't in the controller list | Run setup with the correct Settings folder, then reload FL's device script/list. |
| A command times out | Its changes may already be applied. Run doctor, then read the project state before retrying. |
| House Starter can't find drums | Use three separate loaded channels named Kick, Clap, and Closed Hat. |
| Piano Roll doesn't answer | Focus the intended Piano Roll, run Fruitful Apply manually once, and check your client's Accessibility permission. |
| Sound search rejects the key | Set FREESOUND_API_TOKEN in the MCP client's Fruitful environment, then restart that server. |

Check installed files as well as the connection:

```bash
.venv/bin/fruitful doctor --settings-dir "/your/FL Studio/Settings"
```

Add `--offline` to skip the FL ping, or `--piano-roll` to check that experiment's files and environment.
Doctor never plays, records, or edits notes. It cannot verify Piano Roll focus or permissions.

If it still fails, include the Fruitful/FL versions, the command you tried, and the error message when reporting it.
Remove API keys and personal paths from your report.
