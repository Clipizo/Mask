"""Mask's launcher (runs inside envs/mask).

  mask                       opens Mask in your browser (the same as `mask app`)
       --video FILE          ... with that video already open
  mask check                 shows what is installed and where Mask runs
  mask download [QUALITY]    gets the models: balanced (default), faster, better or all
       --from FOLDER         copies them from a folder instead of downloading them
  mask help                  this text
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common as C  # noqa: E402


def cmd_check() -> int:
    settings = C.load_settings()
    if not settings:
        C.say(f"{C.KIT_NAME} isn't installed yet. Run install-windows.bat (Windows) or bash install.sh (Mac, Linux).")
        return 1
    import onnxruntime as ort
    C.say(f"{C.KIT_NAME} {C.KIT_VERSION}, installed {settings.get('installed', '?')}")
    C.say(f"  ONNX Runtime {ort.__version__}: {', '.join(ort.get_available_providers())}")
    where = {"directml": "the graphics card (DirectML)", "coreml": "the Mac's GPU (Core ML)", "cpu": "the processor"}
    C.say(f"  Runs on: {where.get(settings.get('backend'), settings.get('backend'))}")
    for quality in C.QUALITIES:
        needed = C.models_for(settings, [quality])
        have = [n for n in needed if C.model_is_downloaded(n)]
        C.say(f"  {quality:9s} models: {'ready' if len(have) == len(needed) else f'{len(have)} of {len(needed)} files'}")
    return 0


def cmd_download(quality: str, source: str | None) -> int:
    settings = C.load_settings()
    qualities = C.QUALITIES if quality == "all" else [quality.capitalize()]
    names = [n for n in C.models_for(settings, qualities) if not C.model_is_downloaded(n)]
    if not names:
        C.say("The models are already here.")
        return 0
    folder = Path(source).expanduser() if source else None
    missing = []
    for name in names:
        C.say(f"  {name} ({C.MODEL_FILES[name][0] / 1024**2:.0f} MB)")
        if folder is not None and not (folder / name).is_file():
            missing.append(name)  # copy what the folder has, then say what it lacked
            C.say("    not in that folder")
            continue
        C.fetch_model(name, folder, None if folder else C.console_progress)
    if missing:
        C.say(f"{len(missing)} file(s) aren't in {folder}: {', '.join(missing)}.\n"
              "Copy them from a computer that has them, or download them.")
        return 1
    C.say("The models are ready.")
    return 0


def main(argv=None) -> int:
    C.setup_console()
    parser = argparse.ArgumentParser(prog=C.launcher_command(), description=f"{C.KIT_NAME}: masks for any video, on your own computer")
    parser.add_argument("command", nargs="?", default="app", choices=["app", "check", "download", "help"])
    parser.add_argument("quality", nargs="?", default="balanced", choices=["faster", "balanced", "better", "all"])
    parser.add_argument("--from", dest="source", help="download: copy the models from this folder")
    parser.add_argument("--port", type=int, default=7861, help="app: the first port to try")
    parser.add_argument("--no-browser", action="store_true", help="app: don't open the browser")
    parser.add_argument("--video", help="app: open this video when the page loads")
    args = parser.parse_args(argv)
    try:
        if args.command == "help":
            C.say(__doc__)
            return 0
        if args.command == "check":
            return cmd_check()
        if args.command == "download":
            return cmd_download(args.quality, args.source)
        import webapp
        webapp.main(port=args.port, open_browser=not args.no_browser, video=args.video)
        return 0
    except C.UserError as e:
        C.say(str(e))
        return 1
    except KeyboardInterrupt:
        return 130
    except Exception as e:  # noqa: BLE001
        try:
            (C.KIT / "last-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        C.say(f"Something went wrong: {type(e).__name__}: {e}\n(Details: last-error.txt in the {C.KIT_NAME} folder.)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
