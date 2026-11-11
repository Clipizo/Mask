"""Mask's engine: SAM 2.1 selection and tracking with ONNX Runtime, the way Maskizo does it.

The models and numbers follow Maskizo's native code (MaskizoNative.cpp), so a frame gets the
same mask as in the Resolve plugin:
  - a frame is stretched to 1024 x 1024 (bilinear, pixel centres) and normalised with the
    ImageNet mean and deviation;
  - a selection takes up to 6 points, in that 1024 space (label 1 Keep, 0 Cut, -10 unused);
  - tracking keeps the keyframe's memory and the 15 most recent frames (SAM 2 attends to six
    memories and fifteen object pointers);
  - masks come back as 1024 x 1024 probabilities, stretched back to the frame and rounded to
    0-255.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import common as C

INPUT = 1024
MAX_POINTS = 6
MEMORY_SLOTS = 7      # SAM 2 num_maskmem: the keyframe and six recent frames
POINTER_SLOTS = 16    # SAM 2 max_obj_ptrs_in_encoder
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


# ---------------------------------------------------------------------------
# Pixels in and out (bit for bit Maskizo's formulas, in float32)
# ---------------------------------------------------------------------------

def _axis(out_size: int, in_size: int):
    """Source rows (or columns) and weights for a bilinear stretch through pixel centres."""
    f = (np.arange(out_size, dtype=np.float32) + np.float32(0.5)) * np.float32(in_size) / np.float32(out_size) - np.float32(0.5)
    i0 = np.clip(f.astype(np.int64), 0, in_size - 1)  # C's (int) truncates toward zero
    i1 = np.minimum(i0 + 1, in_size - 1)
    w = np.clip(f - i0.astype(np.float32), np.float32(0), np.float32(1)).astype(np.float32)
    return i0, i1, w


def stretch(image: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    """Bilinear stretch of an H x W (x C) array to out_h x out_w, in float32."""
    y0, y1, wy = _axis(out_h, image.shape[0])
    x0, x1, wx = _axis(out_w, image.shape[1])
    wy, wx = wy[:, None], wx[None, :]
    if image.ndim == 3:
        wy, wx = wy[..., None], wx[..., None]
    one = np.float32(1)
    top, bottom = image[y0], image[y1]
    v = top[:, x0].astype(np.float32) * (one - wx) * (one - wy)
    v = v + top[:, x1].astype(np.float32) * wx * (one - wy)
    v = v + bottom[:, x0].astype(np.float32) * (one - wx) * wy
    v = v + bottom[:, x1].astype(np.float32) * wx * wy
    return v


def preprocess(rgb: np.ndarray) -> np.ndarray:
    """An H x W x 3 RGB frame (uint8) -> the models' 1 x 3 x 1024 x 1024 input."""
    v = stretch(rgb, INPUT, INPUT)
    v = (v / np.float32(255) - MEAN) / STD
    return np.ascontiguousarray(v.transpose(2, 0, 1)[None], dtype=np.float32)


def mask_to_input(alpha: np.ndarray) -> np.ndarray:
    """A frame-size mask (uint8) -> the tracker's 1024 x 1024 mask, binarized at half like SAM 2."""
    v = stretch(alpha, INPUT, INPUT)
    return (v >= np.float32(127.5)).astype(np.float32)[None, None]


def to_alpha(prob: np.ndarray, height: int, width: int) -> np.ndarray:
    """1024 x 1024 probabilities -> a height x width mask, 0-255 (rounded half away from zero)."""
    v = stretch(prob.reshape(INPUT, INPUT), height, width)
    return np.floor(np.clip(v, 0, 1) * np.float32(255) + np.float32(0.5)).astype(np.uint8)


# ---------------------------------------------------------------------------
# Tracking memory
# ---------------------------------------------------------------------------

def empty_bank() -> dict:
    return {"memory": np.zeros((MEMORY_SLOTS, 64, 64, 64), np.float32),
            "memory_valid": np.zeros(MEMORY_SLOTS, np.float32),
            "obj_ptrs": np.zeros((POINTER_SLOTS, 256), np.float32),
            "obj_ptr_pos": np.zeros(POINTER_SLOTS, np.float32),
            "obj_ptr_valid": np.zeros(POINTER_SLOTS, np.float32)}


def fill_bank(key, recent: dict, frame: int, start: int, direction: int, scale: float) -> dict:
    """Slot 0 is the keyframe, slot k the frame k steps back (as Maskizo's fillBank)."""
    bank = empty_bank()

    def put(slot: int, memory, distance: float) -> None:
        maskmem, pointer = memory
        if slot < MEMORY_SLOTS:
            bank["memory"][slot] = maskmem
            bank["memory_valid"][slot] = 1
        bank["obj_ptrs"][slot] = pointer
        bank["obj_ptr_pos"][slot] = np.float32(distance) * np.float32(scale)
        bank["obj_ptr_valid"][slot] = 1

    put(0, key, float((frame - start) * direction))
    for k in range(1, POINTER_SLOTS):
        n = frame - k * direction
        if (n - start) * direction <= 0:
            break
        if n not in recent:
            raise RuntimeError(f"Tracking memory for frame {n} is missing.")
        put(k, recent[n], float(k))
    return bank


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

class Engine:
    """Runs selection and tracking. It keeps one image model and the tracker loaded, so going
    from clicking to tracking and back doesn't load a model again (as Maskizo does: reloading
    costs seconds, and Core ML on a Mac once aborted while loading a model again)."""

    def __init__(self, settings: dict, log=print):
        import onnxruntime as ort
        self.ort = ort
        self.settings = settings
        self.backend = settings.get("backend", "cpu")  # "directml", "coreml" or "cpu"
        self.log = log
        self.slots = {"image": None, "tracker": None}  # each: (file name, on the GPU?, session)
        self.gpu_failed = set()     # model files the GPU couldn't load or run
        self.last_backend = ""      # what the last run used, for the status line

    def gpu_wanted(self, device: str) -> bool:
        return device != "CPU" and self.backend in ("directml", "coreml")

    def release(self, slot: str | None = None) -> None:
        """Unload the image model, the tracker (slot "image" or "tracker"), or both."""
        for name in ([slot] if slot else list(self.slots)):
            self.slots[name] = None

    def _options(self, tracker: bool):
        so = self.ort.SessionOptions()
        so.graph_optimization_level = self.ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        so.log_severity_level = 3
        if self.backend == "directml":
            so.enable_mem_pattern = False
            so.execution_mode = self.ort.ExecutionMode.ORT_SEQUENTIAL
            if tracker:  # DirectML's fused plans run the tracker 5-10x slower (Maskizo, ORT 1.23)
                so.add_session_config_entry("ep.dml.disable_graph_fusion", "1")
        return so

    def _providers(self, gpu: bool):
        if gpu and self.backend == "directml":
            return [("DmlExecutionProvider", {"device_id": 0})]
        if gpu and self.backend == "coreml":
            # No ModelCacheDirectory: a kept-loaded model compiles once per run, 0.3-1.4 s more on
            # an M1, and the cache would take 0.9-2.6 GB of disk.
            return [("CoreMLExecutionProvider", {"ModelFormat": "MLProgram", "MLComputeUnits": "CPUAndGPU",
                                                 "RequireStaticInputShapes": "1"}),
                    "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    def _load(self, name: str, gpu: bool, tracker: bool):
        slot = "tracker" if tracker else "image"
        held = self.slots[slot]
        if held and held[:2] == (name, gpu):
            return held[2]
        self.release(slot)  # this slot's previous model goes first
        if not C.model_is_downloaded(name):
            raise C.UserError(f"The model {name} isn't downloaded yet. Run:  {C.launcher_command()} download")
        path = str(C.model_path(name))
        try:
            session = self.ort.InferenceSession(path, self._options(tracker), providers=self._providers(gpu))
        except Exception:  # noqa: BLE001
            other = "image" if tracker else "tracker"
            if not gpu or self.slots[other] is None:
                raise
            self.release(other)  # perhaps the graphics card is full: free the other model, try once more
            session = self.ort.InferenceSession(path, self._options(tracker), providers=self._providers(gpu))
        self.slots[slot] = (name, gpu, session)
        return session

    def _image_session(self, quality: str, device: str):
        """The image model for this quality: on the GPU if possible, else its CPU twin."""
        notes = []
        if self.gpu_wanted(device):
            name = C.IMAGE_MODELS["gpu" if self.backend == "directml" else "fp32"][quality]
            if name not in self.gpu_failed:
                try:
                    session = self._load(name, True, False)
                    self.last_backend = f"{self.gpu_label()}, {quality}"
                    return session, name, True
                except C.UserError:
                    raise
                except Exception as e:  # noqa: BLE001 - any GPU failure falls back to the CPU
                    self.gpu_failed.add(name)
                    self.release("image")
                    self.log(f"The GPU couldn't load {name} ({type(e).__name__}); using the CPU.")
            notes.append("the GPU couldn't run it")
        if quality == "Better":  # Better has no CPU model: 34 s per selection on an M1's processor
            quality = "Balanced"
            notes.insert(0, "Better needs the GPU")
        name = C.IMAGE_MODELS["fp32"][quality]
        session = self._load(name, False, False)
        self.last_backend = f"CPU, {quality}" + (f" ({'; '.join(notes)})" if notes else "")
        return session, name, False

    def _tracker_session(self, device: str):
        if self.gpu_wanted(device):
            name = C.TRACKER_MODELS["gpu" if self.backend == "directml" else "fp32"]
            if name not in self.gpu_failed:
                try:
                    session = self._load(name, True, True)
                    self.last_backend = self.gpu_label()
                    return session, name, True
                except C.UserError:
                    raise
                except Exception as e:  # noqa: BLE001
                    self.gpu_failed.add(name)
                    self.release("tracker")
                    self.log(f"The GPU couldn't load {name} ({type(e).__name__}); tracking on the CPU.")
        name = C.TRACKER_MODELS["fp32"]
        session = self._load(name, False, True)
        self.last_backend = "CPU"
        return session, name, False

    def gpu_label(self) -> str:
        return "Apple GPU" if self.backend == "coreml" else "GPU"

    def first_choice(self, quality: str | None, device: str = "Auto") -> str:
        """The model file the next selection (quality) or tracking (None) loads, as above."""
        which = "gpu" if self.backend == "directml" else "fp32"
        if quality is None:
            name = C.TRACKER_MODELS[which]
            return name if self.gpu_wanted(device) and name not in self.gpu_failed else C.TRACKER_MODELS["fp32"]
        if self.gpu_wanted(device):
            name = C.IMAGE_MODELS[which][quality]
            if name not in self.gpu_failed:
                return name
        return C.IMAGE_MODELS["fp32"]["Balanced" if quality == "Better" else quality]

    # -----------------------------------------------------------------------
    # Selection
    # -----------------------------------------------------------------------

    def select(self, rgb: np.ndarray, points, quality: str = "Balanced", device: str = "Auto") -> np.ndarray:
        """Mask (uint8, frame size) of the subject the points describe: (x, y, keep) in frame pixels."""
        if not points:
            return np.zeros(rgb.shape[:2], np.uint8)
        height, width = rgb.shape[:2]
        coords = np.zeros((1, 1, MAX_POINTS, 2), np.float32)
        labels = np.full((1, 1, MAX_POINTS), -10, np.int64)
        for k, (x, y, keep) in enumerate(list(points)[-MAX_POINTS:]):
            coords[0, 0, k] = (np.float32(min(max(x / width, 0.0), 1.0)) * INPUT,
                               np.float32(min(max(y / height, 0.0), 1.0)) * INPUT)
            labels[0, 0, k] = 1 if keep else 0
        pixels = preprocess(rgb)
        for attempt in range(2):
            session, name, gpu = self._image_session(quality, device)
            feeds = {"pixel_values": pixels, "input_points": coords, "input_labels": labels}
            if any(i.name == "input_masks" for i in session.get_inputs()):
                feeds["input_masks"] = np.zeros((1, 1, 256, 256), np.float32)
            try:
                prob = session.run(["masks"], feeds)[0]
                return to_alpha(prob, height, width)
            except Exception as e:  # noqa: BLE001 - a GPU that fails while running: once more on the CPU
                if not gpu or attempt:
                    raise
                self.gpu_failed.add(name)
                self.release("image")
                self.log(f"The GPU failed while selecting ({type(e).__name__}); trying the CPU.")
        raise RuntimeError("unreachable")

    # -----------------------------------------------------------------------
    # Tracking
    # -----------------------------------------------------------------------

    def _run_tracker(self, session, pixels, bank, mask, binarize: float, outputs):
        feeds = dict(bank, pixels=pixels, mask=mask, binarize=np.array([binarize], np.float32))
        return session.run(outputs, feeds)

    def track(self, frames, key_rgb: np.ndarray, key_alpha: np.ndarray, start: int, direction: int,
              range_length: int, device: str = "Auto", cancelled=lambda: False):
        """Yields (frame index, mask) for `frames`, an iterable of (index, rgb) going away from the
        keyframe `start` in `direction` (+1 forward, -1 backward). range_length is the number of
        frames in the In/Out range (SAM 2 scales object-pointer distances by it)."""
        session, name, gpu = self._tracker_session(device)

        def run(*args):
            try:
                return self._run_tracker(session, *args)
            except Exception as e:  # noqa: BLE001 - a GPU that fails while tracking: the CPU next time
                if not gpu:
                    raise
                self.gpu_failed.add(name)
                self.release("tracker")
                self.log(f"The GPU failed while tracking ({type(e).__name__}: {e}).")
                raise C.UserError("The graphics card failed while tracking. Track again to use the processor "
                                  "instead (slower).") from e

        height, width = key_rgb.shape[:2]
        window = min(range_length, POINTER_SLOTS) if range_length > 0 else POINTER_SLOTS
        scale = 1.0 / max(1, window - 1)
        maskmem, pointer = run(preprocess(key_rgb), empty_bank(), mask_to_input(key_alpha), 1.0,
                               ["given_maskmem", "given_obj_ptr"])
        key = (maskmem[0], pointer[0])
        recent: dict = {}
        zero_mask = np.zeros((1, 1, INPUT, INPUT), np.float32)
        for index, rgb in frames:
            if cancelled():
                return
            bank = fill_bank(key, recent, index, start, direction, scale)
            prob, pointer, maskmem = run(preprocess(rgb), bank, zero_mask, 0.0, ["mask_prob", "obj_ptr", "maskmem"])
            recent[index] = (maskmem[0], pointer[0])
            for old in [n for n in recent if (index - n) * direction >= POINTER_SLOTS - 1]:
                del recent[old]
            yield index, to_alpha(prob, height, width)


def models_ready(settings: dict, quality: str) -> list[str]:
    """Model files this quality and tracking still need on this computer."""
    return [n for n in C.models_for(settings, [quality]) if not C.model_is_downloaded(n)]


def save_mask(path: Path, alpha: np.ndarray) -> None:
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part.png")
    Image.fromarray(alpha, mode="L").save(partial, compress_level=1)
    partial.replace(path)


def load_mask(path: Path) -> np.ndarray | None:
    from PIL import Image
    try:
        with Image.open(path) as im:
            return np.asarray(im.convert("L"))
    except (OSError, ValueError):
        return None
