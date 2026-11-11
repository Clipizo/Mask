"""Mask's tests. Run them with the kit's Python:

  Windows:      envs\\mask\\Scripts\\python.exe tests\\test_mask.py
  Mac, Linux:   envs/mask/bin/python tests/test_mask.py

The end-to-end tests need the models (models/) and run on the CPU, plus the GPU when the
settings name one. Test files go to .tools/test-run, or to the folder in MASK_TEST_DIR; each run
reuses them.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import common as C  # noqa: E402
import engine as E  # noqa: E402
import video as V  # noqa: E402


def reference_stretch(image: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    """Maskizo's C++ bilinear formula, one pixel at a time (float32 arithmetic)."""
    h, w = image.shape[:2]
    out = np.zeros((out_h, out_w) + image.shape[2:], np.float32)
    f32 = np.float32
    for y in range(out_h):
        fy = (f32(y) + f32(0.5)) * f32(h) / f32(out_h) - f32(0.5)
        y0 = min(max(int(fy), 0), h - 1)
        y1 = min(y0 + 1, h - 1)
        wy = min(max(fy - f32(y0), f32(0)), f32(1))
        for x in range(out_w):
            fx = (f32(x) + f32(0.5)) * f32(w) / f32(out_w) - f32(0.5)
            x0 = min(max(int(fx), 0), w - 1)
            x1 = min(x0 + 1, w - 1)
            wx = min(max(fx - f32(x0), f32(0)), f32(1))
            v = image[y0, x0].astype(np.float32) * (f32(1) - wx) * (f32(1) - wy)
            v = v + image[y0, x1].astype(np.float32) * wx * (f32(1) - wy)
            v = v + image[y1, x0].astype(np.float32) * (f32(1) - wx) * wy
            v = v + image[y1, x1].astype(np.float32) * wx * wy
            out[y, x] = v
    return out


class Pixels(unittest.TestCase):
    def test_stretch_matches_maskizo(self):
        rng = np.random.default_rng(1)
        for shape, size in (((7, 11, 3), (16, 9)), ((5, 3), (12, 20)), ((40, 30, 3), (8, 6))):
            image = rng.integers(0, 256, shape, dtype=np.uint8)
            mine = E.stretch(image, *size)
            reference = reference_stretch(image, *size)
            self.assertLessEqual(float(np.max(np.abs(mine - reference))), 1e-4, shape)

    def test_preprocess_layout(self):
        rgb = np.zeros((20, 30, 3), np.uint8)
        rgb[..., 0] = 255  # pure red
        x = E.preprocess(rgb)
        self.assertEqual(x.shape, (1, 3, 1024, 1024))
        self.assertAlmostEqual(float(x[0, 0, 500, 500]), (1 - 0.485) / 0.229, places=4)
        self.assertAlmostEqual(float(x[0, 1, 500, 500]), (0 - 0.456) / 0.224, places=4)

    def test_alpha_round_trip(self):
        prob = np.zeros((1024, 1024), np.float32)
        prob[256:768, 256:768] = 1
        alpha = E.to_alpha(prob, 100, 200)
        self.assertEqual(alpha.shape, (100, 200))
        self.assertEqual(int(alpha[50, 100]), 255)
        self.assertEqual(int(alpha[5, 5]), 0)
        back = E.mask_to_input(alpha)
        self.assertEqual(back.shape, (1, 1, 1024, 1024))
        self.assertEqual(float(back[0, 0, 512, 512]), 1.0)


class Bank(unittest.TestCase):
    def test_slots(self):
        key = (np.full((64, 64, 64), 9, np.float32), np.full(256, 9, np.float32))
        recent = {n: (np.full((64, 64, 64), n, np.float32), np.full(256, n, np.float32)) for n in range(11, 30)}
        bank = E.fill_bank(key, recent, 30, 10, 1, 1 / 15)
        self.assertEqual(bank["memory_valid"].tolist(), [1] * 7)
        self.assertEqual(float(bank["memory"][1, 0, 0, 0]), 29)   # one frame back
        self.assertEqual(float(bank["memory"][6, 0, 0, 0]), 24)   # six frames back
        self.assertEqual(bank["obj_ptr_valid"].tolist(), [1] * 16)
        self.assertAlmostEqual(float(bank["obj_ptr_pos"][0]), 20 / 15, places=5)  # the keyframe is 20 away
        self.assertAlmostEqual(float(bank["obj_ptr_pos"][3]), 3 / 15, places=5)
        backward = E.fill_bank(key, {9: recent[11]}, 8, 10, -1, 1 / 15)
        self.assertEqual(backward["memory_valid"].tolist(), [1, 1, 0, 0, 0, 0, 0])
        self.assertEqual(backward["obj_ptr_valid"].tolist()[:3], [1, 1, 0])


class Downloads(unittest.TestCase):
    """Model downloads from a local server that drops the first connection halfway."""

    def setUp(self):
        import hashlib
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        self.tmp = Path(os.environ.get("MASK_TEST_DIR") or C.TOOLS / "test-run") / "downloads"
        (self.tmp / "server").mkdir(parents=True, exist_ok=True)
        (self.tmp / "models").mkdir(parents=True, exist_ok=True)
        self.data = np.random.default_rng(3).integers(0, 256, 3 * 1024 * 1024 + 123, dtype=np.uint8).tobytes()
        (self.tmp / "server" / "fake.onnx").write_bytes(self.data)
        for leftover in (self.tmp / "models").glob("fake.onnx*"):  # this test's own files from a previous run
            leftover.replace(self.tmp / "server" / (leftover.name + ".old"))
        data, drops = self.data, {"left": 1}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/fake.onnx":
                    self.send_error(404)
                    return
                start = int(self.headers.get("Range", "bytes=0-")[6:].split("-")[0])
                self.send_response(206 if start else 200)
                if start:
                    self.send_header("Content-Range", f"bytes {start}-{len(data) - 1}/{len(data)}")
                self.send_header("Content-Length", str(len(data) - start))
                self.end_headers()
                if drops["left"] and not start:
                    drops["left"] -= 1
                    self.wfile.write(data[:1024 * 1024])  # then hang up
                    return
                self.wfile.write(data[start:])

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.saved = (C.MODELS, C.MODEL_BASE_URL)
        C.MODELS = self.tmp / "models"
        C.MODEL_BASE_URL = f"http://127.0.0.1:{self.server.server_address[1]}"
        C.MODEL_FILES["fake.onnx"] = (len(self.data), hashlib.sha256(self.data).hexdigest())

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        C.MODELS, C.MODEL_BASE_URL = self.saved
        C.MODEL_FILES.pop("fake.onnx", None)

    def test_resumes_after_a_dropped_connection(self):
        seen = []
        path = C.fetch_model("fake.onnx", progress=lambda name, done, size: seen.append(done))
        self.assertEqual(path.read_bytes(), self.data)
        self.assertIn(1024 * 1024, seen)  # the first connection stopped here, the second went on from it
        self.assertEqual(seen[-1], len(self.data))

    def test_damaged_download_is_set_aside(self):
        C.MODEL_FILES["fake.onnx"] = (len(self.data), "0" * 64)  # a checksum it can't match
        with self.assertRaises(C.UserError):
            C.fetch_model("fake.onnx")
        self.assertFalse((self.tmp / "models" / "fake.onnx").exists())
        self.assertTrue((self.tmp / "models" / "fake.onnx.part.bad").exists())

    def test_missing_file(self):
        C.MODEL_FILES["missing.onnx"] = (10, "0" * 64)
        try:
            with self.assertRaises(C.UserError):
                C.fetch_model("missing.onnx")
        finally:
            C.MODEL_FILES.pop("missing.onnx", None)

    def fetch_with_maskizo(self, content: bytes, progress=None) -> Path:
        """fetch_model with a stand-in for an installed Maskizo that has `content` as fake.onnx."""
        folder = self.tmp / "maskizo"
        folder.mkdir(exist_ok=True)
        (folder / "fake.onnx").write_bytes(content)
        saved = C.maskizo_models
        C.maskizo_models = lambda: folder
        try:
            return C.fetch_model("fake.onnx", progress=progress)
        finally:
            C.maskizo_models = saved

    def test_copies_from_an_installed_maskizo(self):
        seen = []
        path = self.fetch_with_maskizo(self.data, progress=lambda name, done, size: seen.append(done))
        self.assertEqual(path.read_bytes(), self.data)
        self.assertEqual(seen, [])  # copied, not downloaded

    def test_another_maskizo_version_is_downloaded_instead(self):
        path = self.fetch_with_maskizo(bytes(len(self.data)))  # the same size, other content
        self.assertEqual(path.read_bytes(), self.data)


BOX = (260, 120)  # width, height of the white box in the test video


def make_test_video(path: Path, frames: int = 12, size=(480, 270)) -> None:
    """A black video with a white box that moves 6 pixels right per frame."""
    w, h = size
    cmd = [V.ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{w}x{h}", "-r", "24", "-i", "-", "-c:v", "libx264", "-crf", "1", "-pix_fmt", "yuv420p",
           "-g", "5", str(path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(frames):
        image = np.zeros((h, w, 3), np.uint8)
        image[75:75 + BOX[1], 60 + 6 * i:60 + 6 * i + BOX[0]] = 255
        proc.stdin.write(image.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg could not make the test video")


def box_iou(alpha: np.ndarray, index: int) -> float:
    truth = np.zeros(alpha.shape, bool)
    truth[75:75 + BOX[1], 60 + 6 * index:60 + 6 * index + BOX[0]] = True
    mine = alpha >= 128
    return float((mine & truth).sum() / max(1, (mine | truth).sum()))


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reused by every run (its files are overwritten, never piled up); MASK_TEST_DIR moves it.
        cls.tmp = Path(os.environ.get("MASK_TEST_DIR") or C.TOOLS / "test-run")
        cls.tmp.mkdir(parents=True, exist_ok=True)
        cls.path = cls.tmp / "box.mp4"
        make_test_video(cls.path)
        cls.settings = C.load_settings() or {"backend": "cpu"}

    def test_video_index(self):
        video = V.Video(self.path)
        self.assertEqual(video.count, 12)
        self.assertEqual((video.width, video.height), (480, 270))
        self.assertGreater(int(video.frame(7)[140, 60 + 42 + 100].mean()), 200)   # inside the box at frame 7
        self.assertLess(int(video.frame(2)[140, 60 + 12 - 10].mean()), 40)        # left of it at frame 2
        backward = [i for i, _ in video.frames(9, 3, -1)]
        self.assertEqual(backward, [9, 8, 7, 6, 5, 4, 3])
        video.close()

    def _track(self, device: str):
        for name in C.models_for(self.settings, ["Balanced"]):
            if not C.model_is_downloaded(name):
                self.skipTest(f"{name} isn't downloaded")
        engine = E.Engine(self.settings, log=lambda text: None)
        video = V.Video(self.path)
        key = video.frame(0)
        alpha = engine.select(key, [(60 + BOX[0] / 2, 75 + BOX[1] / 2, True)], "Balanced", device)
        self.assertGreater(box_iou(alpha, 0), 0.95, f"selection on {engine.last_backend}")
        masks = {}
        for index, a in engine.track(video.frames(1, 11, 1), key, alpha, 0, 1, 12, device):
            masks[index] = a
        self.assertEqual(sorted(masks), list(range(1, 12)))
        worst = min(box_iou(a, i) for i, a in masks.items())
        self.assertGreater(worst, 0.95, f"tracking on {engine.last_backend}: worst IoU {worst:.3f}")
        last = video.frame(11)
        back = dict(engine.track(video.frames(10, 0, -1), last, masks[11], 11, -1, 12, device))
        self.assertEqual(sorted(back), list(range(0, 11)))
        self.assertGreater(min(box_iou(a, i) for i, a in back.items()), 0.95, "backward tracking")
        video.close()
        return engine, masks, alpha

    def test_cpu(self):
        engine, _, _ = self._track("CPU")
        self.assertTrue(engine.last_backend.startswith("CPU"))

    def test_gpu(self):
        if self.settings.get("backend") not in ("directml", "coreml"):
            self.skipTest("no GPU backend on this computer")
        engine, _, _ = self._track("Auto")
        print(f"\n  GPU run used: {engine.last_backend}")

    def test_export(self):
        engine, masks, alpha = self._track("Auto")
        folder = self.tmp / "masks-export"
        E.save_mask(V.mask_file(folder, 0), alpha)
        for index, a in masks.items():
            if index != 11:  # frame 11 stays without a mask, for the refusal below
                E.save_mask(V.mask_file(folder, index), a)
        video = V.Video(self.path)
        made = {}
        for kind in V.FORMATS:  # overwrite: every test run reuses the same file names
            files = V.export(video, folder, 2, 9, kind, self.tmp / "out" / "box", overwrite=True)
            self.assertTrue(files and files[0].is_file() and files[0].stat().st_size > 0, kind)
            made[kind] = files[0]
        mov = made["Video with transparency (MOV, ProRes 4444)"]
        self.assertEqual(mov.name, "box-alpha.mov")
        probe = subprocess.run([V.ffmpeg_exe(), "-hide_banner", "-i", str(mov)], capture_output=True, text=True).stderr
        self.assertIn("yuva444p", probe)       # ProRes 4444 with alpha
        # Without overwrite, a second export of the same range gets the next free name.
        self.assertEqual(V.free_base(V.FORMATS[2], self.tmp / "out" / "box").name, "box-2")
        self.assertEqual(V.free_base(V.FORMATS[0], self.tmp / "out" / "box").name, "box-2")  # box-masks.zip
        self.assertEqual(V.free_base(V.FORMATS[0], self.tmp / "out" / "unused").name, "unused")
        self.assertTrue((folder / "mask_000011.png").exists() is False)
        with self.assertRaises(C.UserError):   # frames without a mask are refused
            V.export(video, folder, 0, 11, V.FORMATS[0], self.tmp / "out" / "gap")
        video.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
