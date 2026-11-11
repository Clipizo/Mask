"""Shared paths, settings and small helpers for Mask.

Uses only the Python standard library, so the installer (app/setup_kit.py) can import it
before anything is installed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path

KIT_NAME = "Mask"
KIT_VERSION = "0.1.0"

KIT = Path(__file__).resolve().parent.parent
APP = KIT / "app"
ENVS = KIT / "envs"
MODELS = KIT / "models"
OUTPUT = KIT / "output"
TOOLS = KIT / ".tools"
SETTINGS_FILE = ENVS / "settings.json"
ENV_NAME = "mask"

IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"


def env_python(name: str = ENV_NAME) -> Path:
    env = ENVS / name
    return env / "Scripts" / "python.exe" if IS_WINDOWS else env / "bin" / "python"


def launcher_command() -> str:
    """How to start Mask from a terminal in the kit folder, on this system."""
    return "./mask" if not IS_WINDOWS else ".\\mask"


# ---------------------------------------------------------------------------
# The AI models (SAM 2.1 by Meta, Apache License 2.0, exported for ONNX Runtime by Clipizo
# for Maskizo). Each quality has an image model; tracking uses one tracker for all qualities.
#   "gpu": half precision for Windows graphics cards (DirectML)
#   "fp32": full precision, rewritten for Apple's Core ML (Mac GPU); also the CPU model everywhere
# ---------------------------------------------------------------------------

QUALITIES = ["Faster", "Balanced", "Better"]
IMAGE_MODELS = {
    "gpu": {"Faster": "sam2_image_tiny_fp16.onnx", "Balanced": "sam2_image_small_fp16.onnx",
            "Better": "sam2_image_large_fp16.onnx"},
    "fp32": {"Faster": "sam2_image_tiny_coreml.onnx", "Balanced": "sam2_image_small_coreml.onnx",
             "Better": "sam2_image_large_coreml.onnx"},
}
TRACKER_MODELS = {"gpu": "sam2_track_small_fp16.onnx", "fp32": "sam2_track_small_coreml.onnx"}

# Sizes (bytes) and SHA-256 of every model file, checked after each download.
MODEL_FILES = {
    "sam2_image_tiny_fp16.onnx": (65115540, "0de727f6613d9b1e935a8f3640c7b579c8fd5d87bd345c10157c523b4dacc2f7"),
    "sam2_image_small_fp16.onnx": (79361003, "bf0a35d9ecf5faacc98101ea995f4758b9856753e216d1d187069bd1cf452eed"),
    "sam2_image_large_fp16.onnx": (437184298, "6229ac867f641fdd1e473d1894ca0ead9cb00bfabc45d9cfdab1a3cba1bb79e6"),
    "sam2_track_small_fp16.onnx": (105146072, "5cb07c2ddb28b8848d869321cd4c92e81789a4142fb20096fef5d9fa1f37ae3b"),
    "sam2_image_tiny_coreml.onnx": (156628033, "86fb4d28368402c9f15ef47f34f514d86911b1b120024c9ccf44d6945f82c8f7"),
    "sam2_image_small_coreml.onnx": (189228483, "3a266002b95507babe4e8809562877dde2813454385d0a4c74e0dda5a58c6fcd"),
    "sam2_image_large_coreml.onnx": (909605347, "7b0dcb07c64e0cd3879c9adb581caf93cb5ded5859c90897b64a2e9fe379af71"),
    "sam2_track_small_coreml.onnx": (226999585, "3a2dadf24f814d0b517b09df33529717f7257afea6a6cda74021b9d85aad8278"),
}
# Where the installer and the app download models from: <base>/<file name>. Not published yet;
# until then they come from an installed Maskizo, or `mask download --from FOLDER` copies them.
MODEL_BASE_URL = os.environ.get("MASK_MODEL_URL", "")


def model_set(settings: dict) -> str:
    """'gpu' for a Windows graphics card (DirectML), else 'fp32' (Mac GPU through Core ML, or CPU)."""
    return "gpu" if settings.get("backend") == "directml" and settings.get("device") != "cpu" else "fp32"


def model_path(name: str) -> Path:
    return MODELS / name


def model_is_downloaded(name: str) -> bool:
    path = model_path(name)
    size = MODEL_FILES.get(name, (None, None))[0]
    return path.is_file() and (size is None or path.stat().st_size == size)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def models_for(settings: dict, qualities=None, tracker: bool = True) -> list[str]:
    """The model files a quality (or several) and tracking need on this computer."""
    which = model_set(settings)
    names = [IMAGE_MODELS[which][q] for q in (qualities or QUALITIES)]
    if tracker:
        names.append(TRACKER_MODELS[which])
    if which == "gpu":  # the CPU twin, used if the graphics card can't run a model (Better has none)
        names += [IMAGE_MODELS["fp32"][q] for q in (qualities or QUALITIES) if q != "Better"]
        if tracker:
            names.append(TRACKER_MODELS["fp32"])
    return list(dict.fromkeys(names))


def is_cpu_twin(settings: dict, name: str) -> bool:
    """A processor copy that a graphics-card setup only needs if the card can't run a model."""
    return model_set(settings) == "gpu" and name.endswith("_coreml.onnx")


def maskizo_models() -> Path | None:
    """The models folder of an installed Maskizo (Clipizo's masking plugin for DaVinci Resolve).
    It has the same files: the graphics-card ones on Windows, the Mac ones on a Mac."""
    if IS_WINDOWS:
        base = Path(os.environ.get("CommonProgramFiles", r"C:\Program Files\Common Files"))
        folder = base / "OFX" / "Plugins" / "Maskizo.ofx.bundle" / "Contents" / "Win64" / "models"
    elif IS_MAC:
        folder = Path("/Library/OFX/Plugins/Maskizo.ofx.bundle/Contents/Resources/models")
    else:
        return None
    return folder if folder.is_dir() else None


def maskizo_model(name: str) -> Path | None:
    """`name` in an installed Maskizo, if Maskizo has that file (the same size)."""
    folder = maskizo_models()
    found = folder / name if folder is not None else None
    if found is not None and found.is_file() and found.stat().st_size == MODEL_FILES[name][0]:
        return found
    return None


def fetch_model(name: str, source: Path | None = None, progress=None) -> Path:
    """Copy a model from `source` (a folder) or from an installed Maskizo, or download it from
    MODEL_BASE_URL, then check it. progress(name, bytes done, bytes in all) is called as a
    download goes. An interrupted download continues where it stopped."""
    target = model_path(name)
    if model_is_downloaded(name):
        return target
    MODELS.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    size, digest = MODEL_FILES[name]
    local = maskizo_model(name) if source is None else None
    if local is not None:
        shutil.copyfile(local, partial)
        if sha256_file(partial) == digest:
            partial.replace(target)
            return target
        partial.replace(partial.with_name(partial.name + ".bad"))  # another version: download it instead
    if source is not None:
        found = Path(source) / name
        if not found.is_file():
            raise UserError(f"{name} isn't in {source}.")
        shutil.copyfile(found, partial)
    else:
        _download(name, partial, size, progress)
    if partial.stat().st_size != size or sha256_file(partial) != digest:
        partial.replace(partial.with_name(partial.name + ".bad"))
        raise UserError(f"{name} didn't arrive complete. Try again.")
    partial.replace(target)
    return target


def _download(name: str, partial: Path, size: int, progress=None, attempts: int = 5) -> None:
    if not MODEL_BASE_URL:
        raise UserError(f"{KIT_NAME}'s AI models aren't on this computer, and they can't be downloaded yet.\n"
                        f"Copy them in from a folder that has them, in a terminal in the {KIT_NAME} folder:\n"
                        f"  {launcher_command()} download all --from FOLDER")
    import http.client
    import time
    import urllib.error
    import urllib.request
    url = MODEL_BASE_URL.rstrip("/") + "/" + name
    problem = None
    for attempt in range(attempts):
        have = partial.stat().st_size if partial.is_file() else 0
        if have > size:  # not this file: start again
            partial.replace(partial.with_name(partial.name + ".bad"))
            have = 0
        if have == size:
            return
        headers = {"User-Agent": f"{KIT_NAME}/{KIT_VERSION}"}
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
                if have and response.status != 206:  # the server sent the whole file again
                    have = 0
                with partial.open("ab" if have else "wb") as f:
                    done = have
                    while True:
                        block = response.read(1 << 20)
                        if not block:
                            break
                        f.write(block)
                        done += len(block)
                        if progress:
                            progress(name, done, size)
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                raise UserError(f"{name} isn't available for download ({e.code}). Check for a newer {KIT_NAME}.") from None
            problem = f"HTTP {e.code}"
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:  # timeouts, dropped connections
            problem = str(getattr(e, "reason", e)) or type(e).__name__
        if partial.is_file() and partial.stat().st_size == size:
            return
        time.sleep(min(30, 3 * (attempt + 1)))
    raise UserError(f"{name} couldn't be downloaded ({problem or 'the download stopped early'}).\n"
                    "Check your internet connection and try again: it continues where it stopped.")


def console_progress(name: str, done: int, size: int) -> None:
    """A one-line download progress for the terminal."""
    end = "\n" if done >= size else ""
    sys.stdout.write(f"\r    {done / 1024**2:6.0f} of {size / 1024**2:.0f} MB ({100 * done / max(size, 1):3.0f}%)" + end)
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Settings (written by the installer)
# ---------------------------------------------------------------------------

def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(data: dict) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Console and processes
# ---------------------------------------------------------------------------

def setup_console() -> None:
    """Make printing safe on every console (no crashes on unusual characters)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def say(text: str = "") -> None:
    print(text, flush=True)


def child_env() -> dict:
    """Environment variables for the app process."""
    env = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH"):  # set by some other programs; they'd break the environment
        env.pop(name, None)
    env.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONWARNINGS": "ignore",
                "GRADIO_ANALYTICS_ENABLED": "False"})
    return env


class UserError(Exception):
    """A problem the user can fix. The message is shown without a traceback."""


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def safe_name(text: str, max_len: int = 40) -> str:
    """A file-name-safe version of some text."""
    text = unicodedata.normalize("NFKC", text)
    words = re.findall(r"\w+", text)
    return "-".join(words)[:max_len].strip("-_").lower()


def unique_folder(parent: Path, base: str) -> Path:
    """parent/base, or parent/base-2, -3... if that folder is already used."""
    parent.mkdir(parents=True, exist_ok=True)
    candidate, n = parent / base, 2
    while candidate.exists():
        candidate = parent / f"{base}-{n}"
        n += 1
    return candidate


def format_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(int(minutes), 60)
    return f"{hours}:{minutes:02d}:{secs:05.2f}" if hours else f"{minutes}:{secs:05.2f}"
