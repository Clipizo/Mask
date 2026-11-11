"""Video frames in, masks and videos out.

Frames are read with PyAV by their exact index: when a video opens, every frame's presentation
time is listed from the packets (no decoding), so frame N is always the same picture, in display
order and orientation. Exports pair each frame with its mask here and pipe them to the kit's
FFmpeg, so nothing can drift out of step.
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from fractions import Fraction
from pathlib import Path

import numpy as np

import common as C
import engine as E

CHUNK_BYTES = 512 * 1024 * 1024  # frames held at once when tracking backward


class Video:
    """One video file: frames by index (0 = first), RGB, display orientation."""

    def __init__(self, path, index: list | None = None):
        import av
        self.path = Path(path)
        try:
            self.container = av.open(str(self.path))
        except Exception as e:  # noqa: BLE001 - PyAV raises many kinds for unreadable files
            raise C.UserError(f"This file can't be opened as a video ({type(e).__name__}).") from None
        if not self.container.streams.video:
            raise C.UserError("This file has no video picture.")
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"
        rate = self.stream.average_rate or self.stream.guessed_rate or Fraction(25)
        self.rate = Fraction(rate).limit_denominator(1001000)
        self.fps = float(self.rate)
        self.pts = index if index is not None else self._index()
        if not self.pts:
            raise C.UserError("No frames could be read from this video.")
        self.count = len(self.pts)
        self._decoder, self._next = None, None
        first = self.frame(0)
        self.height, self.width = first.shape[:2]

    def _index(self) -> list:
        """Presentation times of every frame, from the packets (fast: nothing is decoded)."""
        import av
        times = []
        with av.open(str(self.path)) as c:
            for packet in c.demux(c.streams.video[0]):
                if packet.pts is not None and packet.size:
                    times.append(packet.pts)
        return sorted(set(times))

    def reader(self) -> "Video":
        """A second reader of the same file (tracking reads while the page shows other frames)."""
        return Video(self.path, self.pts)

    def close(self) -> None:
        try:
            self.container.close()
        except Exception:  # noqa: BLE001
            pass

    def time(self, index: int) -> float:
        return index / self.fps

    def _rgb(self, frame) -> np.ndarray:
        image = frame.to_ndarray(format="rgb24")
        turns = int(round((getattr(frame, "rotation", 0) or 0) / 90)) % 4  # counterclockwise quarter turns
        return np.ascontiguousarray(np.rot90(image, turns)) if turns else image

    def frame(self, index: int) -> np.ndarray:
        index = min(max(int(index), 0), self.count - 1)
        target = self.pts[index]
        # Reading on from the last frame is cheap; anything else seeks to the keyframe before it.
        if self._next is None or index < self._next or index > self._next + 48:
            self.container.seek(target, stream=self.stream, backward=True, any_frame=False)
            self._decoder = self.container.decode(self.stream)
        for frame in self._decoder:
            if frame.pts is None or frame.pts < target:
                continue
            self._next = index + 1
            return self._rgb(frame)
        self._next = None
        raise C.UserError(f"Frame {index} can't be read from this video.")

    def frames(self, start: int, end: int, step: int):
        """(index, rgb) from start to end (inclusive), forward (step 1) or backward (step -1)."""
        if step > 0:
            for index in range(start, end + 1):
                yield index, self.frame(index)
            return
        per_chunk = max(8, CHUNK_BYTES // max(1, self.width * self.height * 3))
        high = start
        while high >= end:
            low = max(end, high - per_chunk + 1)
            block = [(i, self.frame(i)) for i in range(low, high + 1)]  # decoded forward, once
            for item in reversed(block):
                yield item
            high = low - 1


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

FORMATS = ["Mask images (PNG)", "Matte video (MP4)", "Video with transparency (MOV, ProRes 4444)",
           "Video with transparency (WebM)", "Cutout images (PNG with transparency)"]
ENDINGS = dict(zip(FORMATS, ["-masks", "-matte.mp4", "-alpha.mov", "-alpha.webm", "-cutout"]))


def free_base(kind: str, base: Path) -> Path:
    """base, or base-2, -3...: an export never overwrites an earlier one (it may be open in an editor)."""
    ending = ENDINGS[kind]
    candidate, n = base, 2
    while any(Path(str(candidate) + e).exists() for e in (ending, ending + ".zip")):
        candidate = base.with_name(f"{base.name}-{n}")
        n += 1
    return candidate


def ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def mask_file(masks: Path, index: int) -> Path:
    return masks / f"mask_{index:06d}.png"


def missing_masks(masks: Path, first: int, last: int) -> list[int]:
    return [i for i in range(first, last + 1) if not mask_file(masks, i).is_file()]


def _zip(folder: Path) -> Path:
    archive = folder.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as z:  # PNGs are already compressed
        for f in sorted(folder.iterdir()):
            z.write(f, f"{folder.name}/{f.name}")
    return archive


def _encode(cmd: list[str], frames, what: str) -> None:
    """Pipe raw frames to FFmpeg; a failure shows FFmpeg's last lines."""
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for data in frames:
            proc.stdin.write(data)
        proc.stdin.close()
    except (BrokenPipeError, OSError):
        pass
    with proc.stderr:
        err = proc.stderr.read().decode("utf-8", "replace")
    if proc.wait() != 0:
        raise C.UserError(f"Making the {what} failed:\n" + "\n".join(err.strip().splitlines()[-4:]))


def export(video: Video, masks: Path, first: int, last: int, kind: str, base: Path, progress=None,
           overwrite: bool = False) -> list[Path]:
    """Write the In/Out range in one format; returns the files to download. Without overwrite, an
    earlier export of the same range keeps its files and this one is numbered (-2, -3...)."""
    gaps = missing_masks(masks, first, last)
    if gaps:
        raise C.UserError(f"{len(gaps)} frame(s) between In and Out have no mask yet (the first is frame "
                          f"{gaps[0]}). Track them first.")
    if kind not in ENDINGS:
        raise C.UserError(f"Unknown export format: {kind}")
    total = last - first + 1
    base.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite:
        base = free_base(kind, base)
    note = progress or (lambda done, what: None)

    def pairs():
        reader = video.reader()
        try:
            for done, (index, rgb) in enumerate(reader.frames(first, last, 1)):
                alpha = E.load_mask(mask_file(masks, index))
                if alpha is None or alpha.shape != rgb.shape[:2]:
                    raise C.UserError(f"The mask of frame {index} is damaged. Track that frame again.")
                note(done / total, f"Frame {done + 1} of {total}")
                yield index, rgb, alpha
        finally:
            reader.close()

    w, h = video.width, video.height
    rate = f"{video.rate.numerator}/{video.rate.denominator}"
    if kind == "Mask images (PNG)":
        folder = Path(str(base) + "-masks")
        folder.mkdir(parents=True, exist_ok=True)
        for done, index in enumerate(range(first, last + 1)):
            shutil.copyfile(mask_file(masks, index), folder / f"mask_{index:06d}.png")
            note(done / total, f"Frame {done + 1} of {total}")
        return [_zip(folder)]
    if kind == "Cutout images (PNG with transparency)":
        from PIL import Image
        folder = Path(str(base) + "-cutout")
        folder.mkdir(parents=True, exist_ok=True)
        for index, rgb, alpha in pairs():
            Image.fromarray(np.dstack([rgb, alpha]), mode="RGBA").save(folder / f"frame_{index:06d}.png", compress_level=1)
        return [_zip(folder)]
    def raw_input(pix_fmt: str) -> list[str]:
        return [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", pix_fmt,
                "-s", f"{w}x{h}", "-r", rate, "-i", "-"]

    if kind == "Matte video (MP4)":
        out = Path(str(base) + "-matte.mp4")
        cmd = raw_input("gray") + ["-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p", "-c:v", "libx264",
                                   "-crf", "12", "-preset", "medium", "-movflags", "+faststart", str(out)]
        _encode(cmd, (alpha.tobytes() for _, _, alpha in pairs()), "matte video")
        return [out]
    frames = (np.dstack([rgb, alpha]).tobytes() for _, rgb, alpha in pairs())
    if kind == "Video with transparency (MOV, ProRes 4444)":
        out = Path(str(base) + "-alpha.mov")
        _encode(raw_input("rgba") + ["-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le",
                                     "-vendor", "apl0", str(out)], frames, "ProRes video")
        return [out]
    if kind == "Video with transparency (WebM)":
        out = Path(str(base) + "-alpha.webm")
        _encode(raw_input("rgba") + ["-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2:color=black@0", "-c:v", "libvpx-vp9",
                                     "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "24", "-row-mt", "1", str(out)],
                frames, "WebM video")
        return [out]
    raise C.UserError(f"Unknown export format: {kind}")
