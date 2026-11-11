"""Mask in the browser.

mask.py starts this file inside envs/mask (run ./mask, or double-click mask.bat). The page only
runs on this computer (127.0.0.1).

How it works: clicking the picture adds a Keep or Cut point on that frame, which makes it a
keyframe: the subject is selected there at once. Track forward (or backward) follows the subject
from each keyframe to the next one, or to Out (In). In and Out limit tracking and export.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import socket
import subprocess
import threading
import time
import traceback
import uuid
from pathlib import Path

import common as C

# Before Gradio is imported: no usage reports, and its picture cache stays in the kit's folder.
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
os.environ.setdefault("GRADIO_TEMP_DIR", str(C.TOOLS / "gradio"))

import gradio as gr  # noqa: E402 - module level: Gradio resolves the handlers' type hints (gr.SelectData) here
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import engine as E  # noqa: E402
import video as V  # noqa: E402

PREVIEW_MAX = 1280  # longest side of the picture on the page (the masks keep the full size)
LIME = np.array([200, 240, 49], np.float32)
VIEWS = ["Overlay", "Cutout", "Mask", "Original"]
CSS = """
.gradio-container { max-width: 1400px !important; margin: auto; }
footer { display: none !important; }
#frame-view img { cursor: crosshair; }
"""

JOBS: dict[str, "Job"] = {}
ENGINE: E.Engine | None = None
ENGINE_LOCK = threading.Lock()  # one model run at a time (page events run in parallel threads)
DOWNLOAD_LOCK = threading.Lock()  # one model download at a time
BUSY_SECONDS = 30               # tracking that made no progress this long is treated as stopped


class Job:
    """One video being masked: its keyframes (points), In/Out and the masks folder."""

    def __init__(self, path: Path):
        self.video = V.Video(path)
        self.keys: dict[int, list] = {}   # frame -> [[x, y, keep], ...] in frame pixels
        self.first, self.last = 0, self.video.count - 1
        self.frame = 0
        self._cached = None              # (index, rgb) of the last frame read
        self.lock = threading.RLock()    # a video reader serves one thread at a time
        self.tracking = 0.0              # while tracking: when it last finished a frame
        self.stop = False                # Stop tracking was pressed
        self.runs = 0                    # tracking runs started (a stopped run must not touch a newer one)
        self.folder = self._resume(path) or C.unique_folder(C.OUTPUT, C.safe_name(path.stem, 50) or "video")
        self.masks = self.folder / "masks"
        self.exports = self.folder / "exports"
        self.name = self.folder.name
        self.save()

    def _resume(self, path: Path) -> Path | None:
        """The folder of earlier work on this same file (its keyframes, In/Out and masks come back)."""
        base = C.safe_name(path.stem, 50) or "video"
        for folder in sorted(C.OUTPUT.glob(base + "*")):
            try:
                data = json.loads((folder / "job.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if Path(data.get("video", "")) == path and data.get("frames") == self.video.count \
                    and data.get("size") == [self.video.width, self.video.height]:
                self.keys = {int(k): v for k, v in data.get("keyframes", {}).items()}
                self.first = min(max(int(data.get("in", 0)), 0), self.video.count - 1)
                self.last = min(max(int(data.get("out", self.video.count - 1)), self.first), self.video.count - 1)
                return folder
        return None

    def rgb(self, index: int) -> np.ndarray:
        with self.lock:
            if self._cached is None or self._cached[0] != index:
                self._cached = (index, self.video.frame(index))
            return self._cached[1]

    def busy(self) -> bool:
        return bool(self.tracking) and time.time() - self.tracking < BUSY_SECONDS

    def mask(self, index: int) -> np.ndarray | None:
        path = V.mask_file(self.masks, index)
        return E.load_mask(path) if path.is_file() else None

    def save(self) -> None:
        data = {"video": str(self.video.path), "frames": self.video.count, "fps": self.video.fps,
                "size": [self.video.width, self.video.height], "in": self.first, "out": self.last,
                "keyframes": {str(k): v for k, v in sorted(self.keys.items())}}
        self.folder.mkdir(parents=True, exist_ok=True)
        (self.folder / "job.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Drawing the picture
# ---------------------------------------------------------------------------

def checker(height: int, width: int) -> np.ndarray:
    y, x = np.mgrid[0:height, 0:width]
    light = ((y // 16 + x // 16) % 2 == 0)
    return np.where(light[..., None], 205, 160).astype(np.float32) * np.ones(3, np.float32)


def compose(rgb: np.ndarray, alpha: np.ndarray | None, points, view: str) -> np.ndarray:
    """The picture for the page: the frame, its mask in the chosen view, and the points."""
    h, w = rgb.shape[:2]
    scale = min(1.0, PREVIEW_MAX / max(h, w))
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    small = np.asarray(Image.fromarray(rgb).resize(size, Image.BILINEAR), np.float32) if scale < 1 else rgb.astype(np.float32)
    a = None
    if alpha is not None:
        a = np.asarray(Image.fromarray(alpha).resize(size, Image.BILINEAR), np.float32)[..., None] / 255.0 if scale < 1 \
            else alpha.astype(np.float32)[..., None] / 255.0
    if view == "Overlay" and a is not None:
        out = small * (1 - 0.45 * a) + LIME * (0.45 * a)  # tint the selection lime
        out = out * (0.55 + 0.45 * a)                     # and dim what isn't selected
    elif view == "Cutout" and a is not None:
        out = small * a + checker(size[1], size[0]) * (1 - a)
    elif view == "Mask" and a is not None:
        out = np.repeat(a * 255.0, 3, axis=2)
    else:
        out = small
    image = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    if points and view != "Mask":
        draw = ImageDraw.Draw(image)
        radius = max(5, round(min(size) / 90))
        for x, y, keep in points:
            cx, cy = x * scale, y * scale
            fill = (200, 240, 49) if keep else (240, 70, 60)
            draw.ellipse([cx - radius - 2, cy - radius - 2, cx + radius + 2, cy + radius + 2], fill=(20, 20, 20))
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=fill)
    return np.asarray(image)


def picture(job: "Job", view: str) -> np.ndarray:
    return compose(job.rgb(job.frame), job.mask(job.frame), job.keys.get(job.frame), view)


def info_text(job: "Job") -> str:
    v = job.video
    span = job.last - job.first + 1
    tracked = sum(1 for i in range(job.first, job.last + 1) if V.mask_file(job.masks, i).is_file())
    keys = ", ".join(str(k) for k in sorted(job.keys)) or "none yet (click the picture)"
    mark = " · keyframe" if job.frame in job.keys else ""
    return (f"**Frame {job.frame}** of {v.count - 1} ({C.format_time(v.time(job.frame))}){mark}  \n"
            f"In **{job.first}** ({C.format_time(v.time(job.first))}) · Out **{job.last}** "
            f"({C.format_time(v.time(job.last))}) · {span} frames, {tracked} with a mask  \n"
            f"Keyframes: {keys}  \n"
            f"{v.width} x {v.height}, {v.fps:.3f} fps · results in `output/{job.name}`")


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------

def friendly_error(e: BaseException) -> str:
    try:
        (C.KIT / "last-error.txt").write_text(
            f"{C.KIT_NAME} {C.KIT_VERSION}, {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n{traceback.format_exc()}",
            encoding="utf-8")
    except OSError:
        pass
    summary = " ".join(f"{type(e).__name__}: {e}".split())[:200]
    return f"Something went wrong: {summary}\n(Details: last-error.txt in the {C.KIT_NAME} folder.)"


def open_folder(path: Path) -> None:
    try:
        if C.IS_WINDOWS:
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif C.IS_MAC:
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)], stderr=subprocess.DEVNULL)
    except Exception:  # noqa: BLE001
        pass


def build(settings: dict, preload: str | None = None):
    def need(job_id) -> "Job":
        job = JOBS.get(job_id or "")
        if job is None:
            raise gr.Error("Open a video first.", print_exception=False)
        return job

    def idle(job: "Job") -> None:
        if job.busy():
            raise gr.Error("Tracking is running. Wait for it, or press Stop tracking first.", print_exception=False)

    def guarded(fn):
        @functools.wraps(fn)  # Gradio reads the signature to pass SelectData and Progress
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except gr.Error:
                raise
            except C.UserError as e:
                raise gr.Error(str(e), print_exception=False) from None
            except Exception as e:  # noqa: BLE001
                raise gr.Error(friendly_error(e), print_exception=False) from None
        return wrapper

    @guarded
    def open_video(path, view):
        if not path:
            return None, gr.skip(), gr.skip(), "", ""
        path = Path(str(path).strip().strip('"').strip("'")).expanduser()
        if not path.is_file():
            raise C.UserError(f"There is no file at {path}.")
        job = Job(path)
        job_id = uuid.uuid4().hex
        JOBS[job_id] = job
        slider = gr.Slider(minimum=0, maximum=max(1, job.video.count - 1), value=0, step=1, interactive=True)
        return job_id, slider, picture(job, view), info_text(job), "Click the subject to select it."

    @guarded
    def show_frame(job_id, index, view):
        job = need(job_id)
        job.frame = min(max(int(index or 0), 0), job.video.count - 1)
        return picture(job, view), info_text(job)

    @guarded
    def step_frame(job_id, delta, view):
        job = need(job_id)
        job.frame = min(max(job.frame + delta, 0), job.video.count - 1)
        return gr.Slider(value=job.frame), picture(job, view), info_text(job)

    def ensure_model(name: str, what: str, progress) -> None:
        """Download a model the first time it's needed, with a progress bar on the page."""
        if C.model_is_downloaded(name):
            return
        shown = [0.0]

        def note(_, done, size):
            if progress is not None and (done >= size or time.time() - shown[0] > 0.5):
                shown[0] = time.time()
                progress(done / max(size, 1), desc=f"Getting the {what} model, only this once: "
                                                   f"{done / 1024**2:.0f} of {size / 1024**2:.0f} MB")
        with DOWNLOAD_LOCK:
            C.fetch_model(name, None, note)  # returns at once if another event just got it

    def reselect(job: "Job", quality: str, device: str, progress=None) -> str:
        points = job.keys.get(job.frame) or []
        path = V.mask_file(job.masks, job.frame)
        if not points:
            job.keys.pop(job.frame, None)
            if path.is_file():
                path.replace(path.with_name(path.name + ".removed"))
            job.save()
            return "Points cleared on this frame."
        ensure_model(ENGINE.first_choice(quality, device), quality, progress)
        started = time.time()
        rgb = job.rgb(job.frame)
        with ENGINE_LOCK:
            alpha = ENGINE.select(rgb, points, quality, device)
        E.save_mask(path, alpha)
        job.save()
        return f"Selected in {time.time() - started:.1f} s ({ENGINE.last_backend}). Add Keep or Cut points to refine it."

    @guarded
    def click(job_id, quality, mode, device, view, evt: gr.SelectData, progress=gr.Progress()):
        job = need(job_id)
        idle(job)
        rgb = job.rgb(job.frame)
        h, w = rgb.shape[:2]
        scale = min(1.0, PREVIEW_MAX / max(h, w))
        x, y = evt.index[0] / scale, evt.index[1] / scale
        points = job.keys.setdefault(job.frame, [])
        points.append([round(min(max(x, 0), w - 1), 1), round(min(max(y, 0), h - 1), 1), mode == "Keep"])
        del points[:-E.MAX_POINTS]
        status = reselect(job, quality, device, progress)
        return picture(job, view), info_text(job), status

    @guarded
    def undo_point(job_id, quality, device, view, progress=gr.Progress()):
        job = need(job_id)
        idle(job)
        if job.keys.get(job.frame):
            job.keys[job.frame].pop()
        status = reselect(job, quality, device, progress)
        return picture(job, view), info_text(job), status

    @guarded
    def clear_points(job_id, quality, device, view):
        job = need(job_id)
        idle(job)
        job.keys[job.frame] = []
        status = reselect(job, quality, device)
        return picture(job, view), info_text(job), status

    @guarded
    def reselect_all(job_id, quality, device, view, progress=gr.Progress()):
        """Quality changed: select the current keyframe again with the new model."""
        job = JOBS.get(job_id or "")
        if job is None or not job.keys.get(job.frame):
            return gr.skip(), gr.skip()
        if job.busy():
            return gr.skip(), f"{quality} applies to your next click (tracking is running)."
        status = reselect(job, quality, device, progress)
        return picture(job, view), status

    @guarded
    def set_in(job_id):
        job = need(job_id)
        job.first = job.frame
        job.last = max(job.last, job.first)
        job.save()
        return info_text(job)

    @guarded
    def set_out(job_id):
        job = need(job_id)
        job.last = job.frame
        job.first = min(job.first, job.last)
        job.save()
        return info_text(job)

    @guarded
    def whole_video(job_id):
        job = need(job_id)
        job.first, job.last = 0, job.video.count - 1
        job.save()
        return info_text(job)

    def track(job_id, device, view, direction, progress=None):
        job = need(job_id)
        idle(job)
        keys = sorted(k for k in job.keys if job.first <= k <= job.last and job.keys[k])
        if not keys:
            raise gr.Error("Click the subject on a frame between In and Out first: that frame becomes the "
                           "keyframe tracking starts from.", print_exception=False)
        if direction < 0:
            keys = keys[::-1]
        plans = []
        for i, key in enumerate(keys):
            stop = keys[i + 1] - direction if i + 1 < len(keys) else (job.last if direction > 0 else job.first)
            if (stop - key) * direction > 0:
                plans.append((key, stop))
        if not plans:
            raise gr.Error("Nothing to track that way: move In or Out, or add a keyframe.", print_exception=False)
        ensure_model(ENGINE.first_choice(None, device), "tracking", progress)
        total = sum(abs(stop - key) for key, stop in plans)
        done, last, started = 0, None, time.time()
        job.runs += 1
        run = job.runs
        job.tracking, job.stop = time.time(), False
        stopped = lambda: job.stop or job.runs != run  # noqa: E731
        reader = job.video.reader()
        try:
            for key, stop in plans:
                key_alpha = job.mask(key)
                if key_alpha is None:
                    raise C.UserError(f"Keyframe {key} has no mask. Click the subject there again.")
                frames = reader.frames(key + direction, stop, direction)
                steps = ENGINE.track(frames, job.rgb(key), key_alpha, key, direction,
                                     job.last - job.first + 1, device, cancelled=stopped)
                while True:
                    with ENGINE_LOCK:  # held per frame only, so a stopped run can never block the page
                        step = next(steps, None)
                    if step is None:
                        break
                    index, alpha = step
                    E.save_mask(V.mask_file(job.masks, index), alpha)
                    done, last = done + 1, index
                    job.tracking = time.time()
                    rate = done / max(time.time() - started, 1e-6)
                    left = (total - done) / rate if rate else 0
                    status = (f"Tracking: {done} of {total} frames ({ENGINE.last_backend}), "
                              f"{1 / rate:.2f} s per frame, about {C.format_time(left)} left")
                    if done == 1 or done % 5 == 0 or done == total:
                        job.frame = index
                        yield gr.Slider(value=index), picture(job, view), info_text(job), status
                    else:
                        yield gr.skip(), gr.skip(), gr.skip(), status
                if stopped():
                    break
        finally:
            if job.runs == run:
                job.tracking = 0.0
            reader.close()
        took = time.time() - started
        if done:
            job.frame = last  # end on the last frame tracked
        if done < total:
            yield (gr.Slider(value=job.frame), picture(job, view), info_text(job),
                   f"Stopped after {done} of {total} frames.")
            return
        yield (gr.Slider(value=job.frame), picture(job, view), info_text(job),
               f"Tracked {total} frames in {C.format_time(took)} ({ENGINE.last_backend}). Scrub to check them; "
               "click a frame that went wrong to add a keyframe there, then track again.")

    def guarded_track(direction):
        def run(job_id, device, view, progress=gr.Progress()):
            try:
                yield from track(job_id, device, view, direction, progress)
            except gr.Error:
                raise
            except C.UserError as e:
                raise gr.Error(str(e), print_exception=False) from None
            except Exception as e:  # noqa: BLE001
                raise gr.Error(friendly_error(e), print_exception=False) from None
        return run

    @guarded
    def stop_tracking(job_id):
        job = JOBS.get(job_id or "")
        if job is None or not job.tracking:
            return gr.skip(), gr.skip()
        job.stop, job.tracking = True, 0.0
        return info_text(job), "Tracking stopped. The frames it finished keep their masks."

    @guarded
    def export(job_id, kind, progress=gr.Progress()):
        job = need(job_id)
        idle(job)
        base = job.exports / f"{job.name}-{job.first:06d}-{job.last:06d}"
        started = time.time()
        files = V.export(job.video, job.masks, job.first, job.last, kind, base,
                         lambda fraction, what: progress(fraction, desc=what))
        return [str(f) for f in files], f"Exported in {C.format_time(time.time() - started)}: `{files[0].name}`"

    @guarded
    def show_folder(job_id):
        job = JOBS.get(job_id or "")
        folder = job.folder if job else C.OUTPUT
        folder.mkdir(parents=True, exist_ok=True)
        open_folder(folder)
        gr.Info(str(folder), title="Output folder")

    default_quality = "Balanced"
    with gr.Blocks(title=C.KIT_NAME, delete_cache=(3600, 86400)) as demo:
        job_id = gr.State(None)
        gr.Markdown(f"## {C.KIT_NAME}")
        with gr.Row(equal_height=False):
            with gr.Column(scale=1, min_width=300):
                video_in = gr.File(label="Video", file_types=["video"], type="filepath")
                video_path = gr.Textbox(label="Or a file path (big videos: nothing is copied)", max_lines=1,
                                        placeholder=r"C:\Videos\clip.mp4" if C.IS_WINDOWS else "~/Movies/clip.mp4",
                                        value=preload or "")
                quality = gr.Radio(C.QUALITIES, value=default_quality, label="Quality")
                mode = gr.Radio(["Keep", "Cut"], value="Keep", label="A click adds")
                with gr.Row():
                    undo = gr.Button("Undo point", size="sm")
                    clear = gr.Button("Clear points", size="sm")
                gr.Markdown("**Track** between In and Out")
                with gr.Row():
                    back = gr.Button("◀ Backward")
                    forward = gr.Button("Forward ▶", variant="primary")
                stop = gr.Button("Stop tracking", size="sm", variant="stop")
                kind = gr.Dropdown(V.FORMATS, value=V.FORMATS[2], label="Export")
                export_btn = gr.Button("Export", variant="primary")
                files = gr.File(label="Download", file_count="multiple", interactive=False)
                folder = gr.Button("Open the output folder", size="sm")
                with gr.Accordion("More", open=False):
                    device = gr.Radio(["Auto", "CPU"], value="CPU" if settings.get("backend") == "cpu" else "Auto",
                                      label="Run on")
            with gr.Column(scale=3, min_width=480):
                view = gr.Image(label="Click the subject: Keep adds it, Cut removes", type="numpy",
                                interactive=False, elem_id="frame-view", format="png", buttons=["fullscreen"])
                with gr.Row(equal_height=True):
                    prev_btn = gr.Button("◀", size="sm", min_width=50, scale=0)
                    frame = gr.Slider(0, 1, value=0, step=1, label="Frame", interactive=False, scale=10)
                    next_btn = gr.Button("▶", size="sm", min_width=50, scale=0)
                with gr.Row():
                    set_in_btn = gr.Button("Set In", size="sm")
                    set_out_btn = gr.Button("Set Out", size="sm")
                    whole = gr.Button("Whole video", size="sm")
                    show = gr.Radio(VIEWS, value="Overlay", show_label=False, scale=3)
                info = gr.Markdown("")
                status = gr.Markdown("Open a video to start.")

        video_in.change(open_video, [video_in, show], [job_id, frame, view, info, status])
        video_path.submit(open_video, [video_path, show], [job_id, frame, view, info, status])
        if preload:
            demo.load(open_video, [video_path, show], [job_id, frame, view, info, status])
        frame.input(show_frame, [job_id, frame, show], [view, info], trigger_mode="always_last", show_progress="hidden")
        show.change(show_frame, [job_id, frame, show], [view, info], show_progress="hidden")
        prev_btn.click(lambda j, v: step_frame(j, -1, v), [job_id, show], [frame, view, info], show_progress="hidden")
        next_btn.click(lambda j, v: step_frame(j, 1, v), [job_id, show], [frame, view, info], show_progress="hidden")
        view.select(click, [job_id, quality, mode, device, show], [view, info, status])
        undo.click(undo_point, [job_id, quality, device, show], [view, info, status])
        clear.click(clear_points, [job_id, quality, device, show], [view, info, status])
        quality.change(reselect_all, [job_id, quality, device, show], [view, status])
        set_in_btn.click(set_in, job_id, info)
        set_out_btn.click(set_out, job_id, info)
        whole.click(whole_video, job_id, info)
        forward.click(guarded_track(1), [job_id, device, show], [frame, view, info, status])
        back.click(guarded_track(-1), [job_id, device, show], [frame, view, info, status])
        # Stop is a flag the tracking loop checks before each frame: Gradio's own cancel would leave
        # "Error" badges on the picture.
        stop.click(stop_tracking, job_id, [info, status])
        export_btn.click(export, [job_id, kind], [files, status])
        folder.click(show_folder, job_id, None)
    return demo


def free_port(start: int) -> int:
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def main(port: int = 7861, open_browser: bool = True, video: str | None = None) -> None:
    global ENGINE
    settings = C.load_settings()
    ENGINE = E.Engine(settings, log=lambda text: print(text, flush=True))
    C.OUTPUT.mkdir(parents=True, exist_ok=True)
    gr.set_static_paths([str(C.OUTPUT)])  # exports are served from output/, not copied into Gradio's cache
    demo = build(settings, video)
    port = free_port(port)
    print(f"{C.KIT_NAME} is running at http://127.0.0.1:{port}  (close this window to stop it)", flush=True)
    demo.queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1", server_port=port, inbrowser=open_browser, quiet=True, show_error=True,
        footer_links=[], ssr_mode=False, theme=gr.themes.Soft(), css=CSS,
        allowed_paths=[str(C.OUTPUT)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mask in the browser")
    parser.add_argument("--port", type=int, default=7861)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--video", help="open this video when the page loads")
    args = parser.parse_args()
    main(args.port, not args.no_browser, args.video)
