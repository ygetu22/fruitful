# Fruitful

Control FL Studio from your AI assistant. Program drums, adjust channels and plugins, and read your project state.

**macOS beta.** The latest changes passed software checks; a final FL Studio walkthrough is still pending.
Piano Roll tools are experimental.

## Get started

You need **FL Studio**, [uv](https://docs.astral.sh/uv/getting-started/installation/), and an MCP-compatible AI client.
Fruitful uses your client's model access; no AI API key is needed by Fruitful itself.

### 1. Install

Download the source, then install:

```bash
git clone https://github.com/ygetu22/fruitful.git
cd fruitful
uv venv --python 3.12
uv pip install --python .venv/bin/python .
.venv/bin/fruitful setup
```

Setup asks for FL Studio's **Settings** folder. Find it inside the User data folder shown in
**FL Studio → Options → File settings**. Setup installs the device script and prints the command to use in your AI client.

### 2. Connect FL Studio

- Open macOS **Audio MIDI Setup → MIDI Studio → IAC Driver**.
- Enable **Device is online** and add a bus named **Fruitful Request**.
- In FL's **MIDI Settings**, enable that bus as both input and output. Give both the same port number.
- Set the input controller type to **Fruitful**.

Then check the connection:

```bash
.venv/bin/fruitful doctor
```

### 3. Connect your AI client

Add a **local stdio MCP server** named `fruitful`. Paste the command printed by setup. Leave arguments empty.
Keep FL Studio open, then ask: **“Check Fruitful's connection and show me the channels in my project.”**

### 4. Make a beat

In a scratch FL project, load three drum sounds and name their channels **Kick**, **Clap**, and **Closed Hat**.
Select an empty one-bar pattern, then ask:

> Create a house beat at 124 BPM without playing it. Check the drum rows after writing them.

Fruitful writes the current pattern and changes the tempo. Ask it to play when you're ready.
Save a copy before editing: failed operations can leave some changes applied.

## What it does

- Reads and writes drum steps.
- Changes channel volume, pan, names, and mixer routing.
- Inspects and adjusts plugin parameters.
- Reads project state; controls tempo, play, stop, and record.
- Creates a house groove using your loaded drums, then checks the written rows and tempo.
- Provides genre planning notes. It does not automatically produce or export complete songs.

[Piano Roll, sound search, and other optional setup](docs/OPTIONAL_FEATURES.md) ·
[Troubleshooting](docs/TROUBLESHOOTING.md) · [Development and release status](docs/BETA_SCOPE.md)

[MIT license](LICENSE)
