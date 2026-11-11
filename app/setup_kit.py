"""Mask installer.

Started by install-windows.bat (Windows) or install.sh (Mac and Linux).
It uses only the Python standard library.

What it does:
  1. checks your computer (system, memory, disk space)
  2. creates a private Python environment in envs/ with ONNX Runtime, Gradio and the video
     libraries, in versions that are known to work together
  3. tests that everything loads and finds the GPU (any Windows graphics card through DirectML,
     a Mac's GPU through Core ML)
  4. saves the settings in envs/settings.json
  5. gets the AI models

Options (for advanced users and AI agents):
  --yes              don't ask questions (use the recommended answers)
  --download         also get the models now (Balanced and tracking; with --all, every quality)
  --all              with --download: all three qualities
  --no-download      don't offer to get models
  --from FOLDER      copy the models from a folder instead of downloading them
  --repair           delete and rebuild the environment
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common as C  # noqa: E402

PYTHON_VERSION = "3.12"
REQUIREMENTS = C.APP / "requirements" / "mask.txt"
LOG_FILE = C.KIT / "install-log.txt"
UV_NETWORK = {"UV_HTTP_TIMEOUT": "300", "UV_HTTP_CONNECT_TIMEOUT": "60", "UV_HTTP_RETRIES": "8"}
ATTEMPTS = 3

PROBE = r"""
import json, subprocess, sys
r = {"python": sys.version.split()[0]}
try:
    import onnxruntime as ort
    r["onnxruntime"] = ort.__version__
    r["providers"] = ort.get_available_providers()
except Exception as e:
    r["onnxruntime_error"] = f"{type(e).__name__}: {e}"
for name in ("numpy", "PIL", "av", "gradio"):
    try:
        module = __import__(name)
        r[name] = getattr(module, "__version__", "ok")
    except Exception as e:
        r[name + "_error"] = f"{type(e).__name__}: {e}"
try:
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    out = subprocess.run([exe, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    r["ffmpeg"] = exe
    r["encoders"] = [e for e in ("libx264", "prores_ks", "libvpx-vp9") if f" {e} " in out]
except Exception as e:
    r["ffmpeg_error"] = f"{type(e).__name__}: {e}"
print("KIT_PROBE=" + json.dumps(r))
"""


class InstallError(Exception):
    pass


def log(msg: str = "") -> None:
    print(msg, flush=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def step(n: int, total: int, title: str) -> None:
    log("")
    log(f"[{n}/{total}] {title}")
    log("-" * 60)


def ask_yes_no(question: str, default: bool, assume_yes: bool) -> bool:
    if assume_yes or not sys.stdin.isatty():
        return default
    hint = "Y/n" if default else "y/N"
    while True:
        try:
            a = input(f"{question} ({hint}): ").replace("\ufeff", "").strip().lower()
        except EOFError:
            return default
        if not a:
            return default
        if a in ("y", "yes"):
            return True
        if a in ("n", "no"):
            return False


def run(cmd: list[str], what: str) -> None:
    """Run an install command. Downloads that fail (usually an internet hiccup) are tried again."""
    for attempt in range(1, ATTEMPTS + 1):
        log("  > " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
        code = subprocess.call(cmd, cwd=str(C.KIT))
        log(f"  (exit code {code})")
        if code == 0:
            return
        if attempt < ATTEMPTS:
            log("  That didn't work, usually because of a short internet problem. Trying again in 15 seconds")
            log(f"  (attempt {attempt + 1} of {ATTEMPTS}). What is already downloaded is kept.")
            time.sleep(15)
    raise InstallError(
        f"{what} failed, {ATTEMPTS} times.\n"
        "This is usually an internet problem: the connection dropped, or a school, work or\n"
        "country network blocks the download. Check your connection, then run the installer\n"
        "again: it keeps what it already downloaded and continues.")


# ---------------------------------------------------------------------------
# Detecting the computer
# ---------------------------------------------------------------------------

def ram_gb() -> float | None:
    try:
        if C.IS_WINDOWS:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
            return stat.ullTotalPhys / 1024**3
        if C.IS_MAC:
            out = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout
            return int(out.strip()) / 1024**3
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / 1024**2
    except Exception:
        return None
    return None


def apple_silicon() -> bool:
    if not C.IS_MAC:
        return False
    if platform.machine().lower() == "arm64":
        return True
    out = subprocess.run(["sysctl", "-n", "hw.optional.arm64"], capture_output=True, text=True).stdout
    return out.strip() == "1"


def detect() -> dict:
    info = {
        "os": "macOS" if C.IS_MAC else platform.system(),
        "os_version": (platform.mac_ver()[0] or platform.release()) if C.IS_MAC else platform.release(),
        "machine": platform.machine().lower(),
        "ram_gb": ram_gb(),
        "apple_silicon": apple_silicon(),
    }
    if info["os"] == "Linux":
        try:
            name = platform.freedesktop_os_release().get("PRETTY_NAME")
            if name:
                info["os"], info["os_version"] = name, ""
        except OSError:
            pass
    try:
        info["disk_free_gb"] = shutil.disk_usage(C.KIT).free / 1024**3
    except OSError:
        info["disk_free_gb"] = None
    return info


def check_supported(info: dict) -> None:
    if C.IS_MAC and not info["apple_silicon"]:
        raise InstallError(f"This Mac has an Intel processor. {C.KIT_NAME} needs a Mac with Apple Silicon (M1 or newer).\n"
                           "You can use it on a Windows or Linux PC instead.")
    if C.IS_WINDOWS and info["machine"] in ("arm64", "aarch64"):
        raise InstallError("Windows on ARM (for example Snapdragon laptops) isn't supported yet.")
    if info["machine"] not in ("x86_64", "amd64", "arm64", "aarch64"):
        raise InstallError(f"This kind of processor ({info['machine']}) isn't supported.")


def check_folder(assume_yes: bool) -> None:
    path = str(C.KIT)
    short = f"C:\\{C.KIT_NAME}"
    problems = []
    if C.IS_WINDOWS:
        low = path.lower()
        if "\\appdata\\local\\temp" in low or ".zip" in low:
            raise InstallError(
                "It looks like you started the installer from inside the ZIP file.\n"
                "Please extract (unzip) the folder first: right-click the ZIP > Extract All...\n"
                f"Then move the folder to {short} and run install-windows.bat from there.")
        if len(path) > 60:
            problems.append(f"The folder path is long ({len(path)} characters). Windows can fail on long paths.\n"
                            f"  Recommended: move the folder to {short} and run the installer again.")
    if "onedrive" in path.lower() or "icloud" in path.lower() or "dropbox" in path.lower():
        problems.append("This folder is synced to the cloud (OneDrive, iCloud or Dropbox). The models and your\n"
                        "  results are large and would be uploaded. Recommended: move the folder outside it,\n"
                        f"  for example to {short} (Windows) or your home folder (Mac).")
    if not path.isascii():
        problems.append("The folder path contains special characters. If something fails, move the folder\n"
                        f"  to a simple path like {short}.")
    for p in problems:
        log("WARNING: " + p)
    if problems and not ask_yes_no("Continue anyway?", default=True, assume_yes=assume_yes):
        raise InstallError("Install stopped. Move the folder and run the installer again.")


VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
VC_REDIST_HELP = ("Windows is missing a free Microsoft component that ONNX Runtime needs: the\n"
                  "'Microsoft Visual C++ Redistributable'. Download it from Microsoft and run it:\n"
                  f"  {VC_REDIST_URL}\n"
                  "Then restart the computer and run this installer again.")


def windows_runtime_missing() -> list[str]:
    if not C.IS_WINDOWS:
        return []
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    return [n for n in ("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll") if not (system32 / n).exists()]


def install_windows_runtime(assume_yes: bool) -> bool:
    """Download Microsoft's Visual C++ Redistributable and install it (Windows asks the user for
    permission). Returns False if it wasn't installed; the caller then explains the manual fix."""
    log("  ONNX Runtime needs a free Microsoft component, the 'Microsoft Visual C++ Redistributable'.")
    if not ask_yes_no("  Install it now? (Windows will ask for permission: click Yes)", default=True,
                      assume_yes=assume_yes):
        return False
    try:
        import urllib.request

        exe = C.TOOLS / "vc_redist.x64.exe"
        exe.parent.mkdir(parents=True, exist_ok=True)
        log("  Downloading it from Microsoft (about 25 MB)...")
        with urllib.request.urlopen(VC_REDIST_URL, timeout=120) as response, exe.open("wb") as f:
            shutil.copyfileobj(response, f)
        log("  Installing it. When Windows asks for permission, click Yes.")
        powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        script = ("$p = Start-Process -FilePath $env:KIT_VC_REDIST -ArgumentList '/install','/passive','/norestart' "
                  "-Verb RunAs -Wait -PassThru; exit $p.ExitCode")
        code = subprocess.call([str(powershell) if powershell.exists() else "powershell", "-NoProfile",
                                "-ExecutionPolicy", "Bypass", "-Command", script],
                               env=dict(os.environ, KIT_VC_REDIST=str(exe)))
        log(f"  (exit code {code})")
    except Exception as e:  # no internet, permission refused...: fall back to the manual fix
        log(f"  It couldn't be installed automatically ({type(e).__name__}: {e}).")
        return False
    if code not in (0, 1638, 3010) or windows_runtime_missing():  # 1638: a newer one is installed
        return False
    log("  OK: the Microsoft component is installed.")
    return True


# ---------------------------------------------------------------------------
# Installing
# ---------------------------------------------------------------------------

def find_uv() -> str:
    candidates = [os.environ.get("KIT_UV", "")]
    exe = "uv.exe" if C.IS_WINDOWS else "uv"
    candidates += [str(C.TOOLS / "uv" / exe), str(C.TOOLS / "uv" / "bin" / exe), shutil.which("uv") or ""]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise InstallError("I couldn't find 'uv' (the tool that installs Python). Run the installer\n"
                       "with install-windows.bat or install.sh instead of running this file directly.")


def env_works(py: Path) -> bool:
    """False if the environment is broken, for example after the folder was moved."""
    try:
        proc = subprocess.run([str(py), "-c", "import sys; print(sys.prefix)"], capture_output=True,
                              text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if proc.returncode != 0:
        return False
    try:
        return Path(proc.stdout.strip()).resolve() == py.parent.parent.resolve()
    except OSError:
        return False


def remove_env(env_dir: Path) -> None:
    try:
        shutil.rmtree(env_dir)
    except OSError as e:
        raise InstallError(
            f"I couldn't remove the old environment (envs/{env_dir.name}): {e}\n"
            f"Close every {C.KIT_NAME} window (including the browser app), then run the installer again.\n"
            "If it still fails, restart the computer and try again.") from e


def install_env(uv: str, repair: bool) -> None:
    env_dir = C.ENVS / C.ENV_NAME
    py = C.env_python()
    if repair and env_dir.exists():
        log("  Removing the old environment...")
        remove_env(env_dir)
    elif py.exists() and not env_works(py):
        log("  The environment is broken (was the folder moved?). Rebuilding it...")
        remove_env(env_dir)
    if not py.exists():
        if env_dir.exists():
            remove_env(env_dir)
        run([uv, "venv", str(env_dir), "--python", PYTHON_VERSION, "--quiet"], "Creating the environment")
    else:
        log("  The environment already exists; checking it.")
    log("  Downloading ONNX Runtime, Gradio and the video libraries (about 300 MB).")
    run([uv, "pip", "install", "--python", str(py), "--no-deps", "-r", str(REQUIREMENTS)],
        "Installing the packages")
    code = subprocess.call([uv, "pip", "check", "--python", str(py)], cwd=str(C.KIT))
    if code != 0:
        log("  (uv pip check reported the issues above; continuing, the test below decides.)")


def probe() -> dict:
    proc = subprocess.run([str(C.env_python()), "-c", PROBE], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=C.child_env(), cwd=str(C.KIT))
    for line in proc.stdout.splitlines():
        if line.startswith("KIT_PROBE="):
            return json.loads(line.split("=", 1)[1])
    return {"error": (proc.stderr or proc.stdout)[-800:]}


def make_settings(info: dict, p: dict) -> dict:
    providers = p.get("providers") or []
    if C.IS_WINDOWS and "DmlExecutionProvider" in providers:
        backend = "directml"
    elif C.IS_MAC and info.get("apple_silicon") and "CoreMLExecutionProvider" in providers:
        backend = "coreml"
    else:
        backend = "cpu"
    return {"kit": C.KIT_NAME, "kit_version": C.KIT_VERSION, "backend": backend,
            "device": "cpu" if backend == "cpu" else "auto", "ram_gb": round(info.get("ram_gb") or 0),
            "installed": time.strftime("%Y-%m-%d %H:%M")}


def make_shortcut() -> None:
    """On Mac and Linux, add ./mask (a link to mask.sh), so the command is the same as on Windows."""
    if C.IS_WINDOWS:
        return
    link = C.KIT / "mask"
    try:
        if link.is_symlink():
            if os.readlink(link) == "mask.sh":
                return
            link.unlink()
        elif link.exists():
            return
        os.symlink("mask.sh", link)
    except OSError:
        pass


def describe(info: dict) -> None:
    system = " ".join(p for p in (info["os"], info["os_version"]) if p)
    log(f"  System:     {system} ({info['machine']})")
    if info.get("ram_gb"):
        log(f"  Memory:     {info['ram_gb']:.0f} GB")
    if info.get("disk_free_gb") is not None:
        log(f"  Free disk:  {info['disk_free_gb']:.0f} GB")


def get_models(settings: dict, everything: bool, source: Path | None) -> None:
    names = [n for n in C.models_for(settings, None if everything else ["Balanced"]) if not C.model_is_downloaded(n)]
    if not names:
        log("  The models are already here.")
        return
    total = sum(C.MODEL_FILES[n][0] for n in names) / 1024**3
    log(f"  Getting {len(names)} model file(s), about {total:.1f} GB.")
    for name in names:
        log(f"  {name}")
        C.fetch_model(name, source, None if source else C.console_progress)
    log("  OK: the models are ready.")


def main() -> int:
    C.setup_console()
    parser = argparse.ArgumentParser(description=f"{C.KIT_NAME} installer")
    parser.add_argument("--yes", action="store_true", help="don't ask questions")
    parser.add_argument("--download", action="store_true", help="also get the models now")
    parser.add_argument("--all", action="store_true", help="with --download: every quality")
    parser.add_argument("--no-download", action="store_true", help="don't offer to get models")
    parser.add_argument("--from", dest="source", help="copy the models from this folder")
    parser.add_argument("--repair", action="store_true", help="rebuild the environment from scratch")
    args = parser.parse_args()
    for name, value in UV_NETWORK.items():
        os.environ.setdefault(name, value)
    try:
        LOG_FILE.write_text(f"{C.KIT_NAME} {C.KIT_VERSION} install log, {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
                            encoding="utf-8")
    except OSError:
        pass

    log("")
    log("=" * 60)
    log(f"  {C.KIT_NAME} {C.KIT_VERSION} installer")
    log("=" * 60)
    log(f"This sets up everything {C.KIT_NAME} needs inside this folder. It takes")
    log("2 to 15 minutes, depending on your internet connection.")
    total = 5
    try:
        step(1, total, "Checking your computer")
        info = detect()
        describe(info)
        check_supported(info)
        check_folder(args.yes)
        if windows_runtime_missing() and not install_windows_runtime(args.yes):
            log("WARNING: " + VC_REDIST_HELP)
        free = info.get("disk_free_gb")
        if free is not None and free < 6:
            log(f"WARNING: only {free:.0f} GB free. {C.KIT_NAME} needs about 1 GB for the programs, up to")
            log("         2 GB for the models, and room for your results.")
            if not ask_yes_no("Continue anyway?", default=free >= 3, assume_yes=args.yes):
                raise InstallError("Install stopped. Free up disk space and run the installer again.")

        uv = find_uv()
        C.ENVS.mkdir(parents=True, exist_ok=True)
        step(2, total, "Installing Python, ONNX Runtime, Gradio and the video libraries")
        install_env(uv, args.repair)

        step(3, total, "Testing the installation")
        p = probe()
        problems = [f"{k[:-6]}: {v}" for k, v in p.items() if k.endswith("_error")] or ([p["error"]] if "error" in p else [])
        if problems:
            raise InstallError("The installation doesn't load:\n  " + "\n  ".join(problems))
        missing = [e for e in ("libx264", "prores_ks", "libvpx-vp9") if e not in p.get("encoders", [])]
        log(f"  OK: Python {p.get('python')}, ONNX Runtime {p.get('onnxruntime')}, Gradio {p.get('gradio')}, PyAV {p.get('av')}")
        if missing:
            log(f"WARNING: the video converter lacks {', '.join(missing)}; those export formats won't work.")

        step(4, total, "Saving settings")
        settings = make_settings(info, p)
        C.save_settings(settings)
        where = {"directml": "your graphics card (DirectML)", "coreml": "the Mac's GPU (Core ML)",
                 "cpu": "the processor (slower)"}[settings["backend"]]
        log(f"  Runs on: {where}.")
        if not C.IS_WINDOWS:
            for f in ("mask.sh", "install.sh"):
                try:
                    os.chmod(C.KIT / f, 0o755)
                except OSError:
                    pass
            make_shortcut()
        for d in (C.OUTPUT, C.MODELS):
            d.mkdir(exist_ok=True)

        step(5, total, "Getting the AI models")
        source = Path(args.source).expanduser() if args.source else None
        if source or C.MODEL_BASE_URL:
            want = args.download or source is not None or (not args.no_download and not args.yes and ask_yes_no(
                "Get the AI models now? (otherwise they come the first time you use them)", default=True,
                assume_yes=False))
            if want:
                try:
                    get_models(settings, args.all, source)
                except C.UserError as e:
                    log(f"  The models aren't ready: {e}")
        else:
            log(f"  Skipped: the models aren't published for download yet. Copy them in with:")
            log(f"    {C.launcher_command()} download --from FOLDER")
    except InstallError as e:
        log("")
        log("!" * 60)
        log(str(e))
        log("!" * 60)
        log(f"A log was saved to {LOG_FILE.name}. If you're stuck, give that file (or the text above)")
        log("to your AI assistant.")
        return 1
    except KeyboardInterrupt:
        log("\nInstall stopped. Run the installer again to continue where it stopped.")
        return 130

    log("")
    log("=" * 60)
    log(f"  {C.KIT_NAME} is installed!")
    log("=" * 60)
    if C.IS_WINDOWS:
        log("Start it: double-click  mask.bat  in this folder. It opens in your browser.")
    else:
        log(f"Start it from Terminal, in this folder:  {C.launcher_command()}   (it opens in your browser)")
    if settings["backend"] == "cpu":
        log("")
        log("Note: no supported GPU, so the AI runs on the processor. It works, but tracking is slow")
        log("(a few seconds per frame), and Better quality uses Balanced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
