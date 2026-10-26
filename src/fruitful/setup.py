"""Install the FL-side scripts from a checkout or an installed wheel."""

import tempfile
from importlib.resources import files
from pathlib import Path


def script_source(name: str) -> str:
    bundled = files("fruitful").joinpath("resources", name)
    if bundled.is_file():
        return bundled.read_text(encoding="utf-8")
    # Editable installs use the original scripts rather than a second copy.
    folder = "device" if name == "device_Fruitful.py" else "pianoroll"
    source = Path(__file__).resolve().parents[2] / folder / name
    if not source.is_file():
        raise ValueError(
            "The installation is missing FL scripts. Reinstall Fruitful from a complete release."
        )
    return source.read_text(encoding="utf-8")


def settings_directory(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if path.name != "Settings" or not path.is_dir():
        raise ValueError(
            "Choose the existing Settings folder inside FL Studio's User data folder "
            "(Options > File settings). Custom drives are supported."
        )
    return path


def installation_files(settings: Path, piano_roll: bool) -> dict[Path, str]:
    result = {
        settings / "Hardware/Fruitful/device_Fruitful.py": script_source("device_Fruitful.py")
    }
    if piano_roll:
        directory = settings / "Piano roll scripts"
        source = script_source("Fruitful Apply.pyscript")
        source = source.replace('"__FRUITFUL_PIANO_ROLL_DIR__"', repr(str(directory)))
        result[directory / "Fruitful Apply.pyscript"] = source
    return result


def install_scripts(settings: Path, piano_roll: bool, dry_run: bool, force: bool) -> None:
    scripts = installation_files(settings, piano_roll)
    # Check every destination before writing any file.
    for path, content in scripts.items():
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError(f"Cannot install over a symlink or directory: {path}")
        if path.exists() and path.read_text(encoding="utf-8") != content and not force:
            raise ValueError(
                f"Existing script differs: {path}. Back it up, then repeat with --force to replace it."
            )

    for path, content in scripts.items():
        if path.exists() and path.read_text(encoding="utf-8") == content:
            print(f"Already installed: {path}")
            continue
        if dry_run:
            print(f"Would install: {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        # Replace complete scripts so FL cannot load a half-written file.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent, delete=False
            ) as output:
                temporary = Path(output.name)
                output.write(content)
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        print(f"Installed: {path}")

    if dry_run:
        print("Preview only; no files changed.")
    else:
        print(
            "Next: enable Fruitful Request input/output in FL MIDI Settings, using the same port number."
        )
        print(
            "Select the Fruitful controller, then run fruitful doctor. Reload the script if FL was already open."
        )
    if piano_roll:
        print(
            f"Set FRUITFUL_PIANO_ROLL_DIR in your MCP client environment to: {settings / 'Piano roll scripts'}"
        )
        print(
            "Piano Roll is experimental: follow the additional permissions and shortcut steps in README.md."
        )
