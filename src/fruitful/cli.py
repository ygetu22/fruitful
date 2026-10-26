"""Local setup commands; invoking fruitful without a subcommand starts MCP."""

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .setup import install_scripts, installation_files, settings_directory


def setup(value: str | None) -> None:
    """Ask once for FL's Settings folder, then show the remaining connection steps."""
    if value is None:
        default = Path.home() / "Documents/Image-Line/FL Studio/Settings"
        print("Find your User data folder in FL Studio: Options > File settings.")
        suggestion = f" [{default}]" if default.is_dir() else ""
        try:
            value = input(f"Settings folder{suggestion}: ").strip()
        except EOFError:
            raise ValueError(
                "Supply your Settings folder with fruitful setup --settings-dir <folder>."
            ) from None
        if not value and default.is_dir():
            value = str(default)
        value = value.strip("\"'")
    install_scripts(settings_directory(value), piano_roll=False, dry_run=False, force=False)
    print("\nIn your MCP client, add a local stdio server named fruitful.")
    print(f"Command: {Path(sys.executable).with_name('fruitful').absolute()}")
    print("Arguments: none. Then ask it to check Fruitful's connection.")


def doctor(settings: Path | None, offline: bool, piano_roll: bool) -> int:
    """Inspect installation and optionally send a read-only FL connection ping."""
    print(f"Fruitful {__version__} — Python {sys.version.split()[0]} — {sys.platform}")
    if sys.platform != "darwin":
        print("FAIL: This beta supports macOS only. Windows/Linux setup has not been validated.")
        return 1

    failed = False
    if settings is not None:
        for path, expected in installation_files(settings, piano_roll).items():
            if not path.is_file():
                print(f"FAIL: Missing script: {path}")
                failed = True
            elif path.read_text(encoding="utf-8") != expected:
                print(f"FAIL: Script differs from this Fruitful installation: {path}")
                print(
                    "Back it up and reinstall using fruitful install-scripts --settings-dir ... --force."
                )
                failed = True
            else:
                print(f"OK: Installed script: {path}")
    else:
        print(
            "SKIP: Script locations unchecked. Supply --settings-dir with your FL Settings folder."
        )

    if piano_roll:
        configured = os.environ.get("FRUITFUL_PIANO_ROLL_DIR")
        expected_dir = settings / "Piano roll scripts" if settings else None
        if not configured or not Path(configured).expanduser().is_dir():
            print("FAIL: Set FRUITFUL_PIANO_ROLL_DIR to the installed Piano roll scripts folder.")
            failed = True
        elif expected_dir and Path(configured).expanduser().resolve() != expected_dir:
            print("FAIL: FRUITFUL_PIANO_ROLL_DIR does not match the selected Settings folder.")
            failed = True
        else:
            print("OK: Piano Roll directory configured.")
        print(
            "SKIP: Accessibility permission, shortcut, and target Piano Roll require a manual check."
        )

    try:
        import mido

        from .bridge import REQUEST_PORT, Bridge, BridgeError, _find_port

        inputs = mido.get_input_names()
        outputs = mido.get_output_names()
        print(f"MIDI inputs: {', '.join(inputs) or 'none'}")
        print(f"MIDI outputs: {', '.join(outputs) or 'none'}")
        _find_port(REQUEST_PORT, inputs)
        _find_port(REQUEST_PORT, outputs)
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f"FAIL: MIDI setup unavailable: {error}")
        print("Enable the IAC Driver in Audio MIDI Setup and create a bus named Fruitful Request.")
        print("If the MIDI backend is missing, reinstall Fruitful in its Python 3.12 environment.")
        return 1

    print("OK: Fruitful Request MIDI input and output found.")
    if offline:
        print(
            "SKIP: FL connection ping (--offline). MIDI port presence alone does not confirm FL is connected."
        )
    else:
        bridge = Bridge()
        try:
            result = bridge.call("ping")
            if not isinstance(result, dict) or result.get("pong") is not True:
                raise BridgeError("Unexpected ping reply. Reinstall the matching FL device script.")
            print(
                f"OK: FL Studio replied (reported version: {result.get('fl_version', 'unknown')})."
            )
        except (OSError, RuntimeError, ValueError) as error:
            print(f"FAIL: FL connection: {error}")
            print(
                "Open FL Studio. Enable Fruitful Request input/output, assign the Fruitful controller,"
            )
            print(
                "and use the same FL port number for both. Check View > Script output for script errors."
            )
            failed = True
        finally:
            bridge.close()
    print(
        "Setup checks failed."
        if failed
        else "Requested checks passed; see SKIP lines for unverified steps."
    )
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Fruitful macOS beta: local FL Studio MCP bridge.")
    parser.add_argument("--version", action="version", version=f"Fruitful {__version__}")
    commands = parser.add_subparsers(dest="command")
    guided = commands.add_parser("setup", help="Install the FL script and show connection steps.")
    guided.add_argument("--settings-dir", help="FL User data folder's existing Settings directory.")
    install = commands.add_parser(
        "install-scripts", help="Install FL scripts into your chosen Settings folder."
    )
    install.add_argument(
        "--settings-dir", required=True, help="Existing FL User data folder's Settings directory."
    )
    install.add_argument(
        "--piano-roll", action="store_true", help="Also install the experimental Piano Roll script."
    )
    install.add_argument(
        "--dry-run", action="store_true", help="Show destinations without writing files."
    )
    install.add_argument(
        "--force", action="store_true", help="Replace differing scripts; back them up first."
    )
    check = commands.add_parser("doctor", help="Check setup and send a read-only connection ping.")
    check.add_argument(
        "--settings-dir", help="Also check installed FL scripts against this version."
    )
    check.add_argument(
        "--offline", action="store_true", help="Inspect files and MIDI ports without contacting FL."
    )
    check.add_argument(
        "--piano-roll", action="store_true", help="Also inspect experimental Piano Roll setup."
    )
    args = parser.parse_args()

    try:
        if args.command in {"setup", "install-scripts"}:
            if sys.platform != "darwin":
                raise ValueError("This beta's installer supports macOS only.")
            if args.command == "setup":
                setup(args.settings_dir)
            else:
                install_scripts(
                    settings_directory(args.settings_dir), args.piano_roll, args.dry_run, args.force
                )
        elif args.command == "doctor":
            settings = settings_directory(args.settings_dir) if args.settings_dir else None
            raise SystemExit(doctor(settings, args.offline, args.piano_roll))
        else:
            from .server import _bridge, mcp

            try:
                mcp.run()
            finally:
                _bridge.close()
    except (OSError, ValueError) as error:
        parser.exit(1, f"Fruitful: {error}\n")


if __name__ == "__main__":
    main()
