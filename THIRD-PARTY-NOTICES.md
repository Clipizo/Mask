# Third-party notices

Mask is an unofficial kit made by Clipizo. It is **not affiliated with, sponsored by or endorsed by Meta.** "Segment Anything" and "SAM" are used here only to describe which models the kit works with.

This repository contains only Mask's own files. It does **not** include the AI models or the libraries below. The installer and the first run download them (the libraries from PyPI and Astral, the models from Clipizo), and each one stays under its own license.

## AI models

| Model | Made by | License | Source |
|---|---|---|---|
| SAM 2.1 (hiera tiny, small and large) | Meta | Apache License 2.0 | https://github.com/facebookresearch/sam2 |

Mask downloads copies of these models that Clipizo converted to the ONNX format (the image models for clicking, and the video tracker), in half precision for Windows graphics cards and in full precision for Macs and processors. The conversion changes the file format, the precision and the graph layout, not what the models were trained to do. The converted files stay under the Apache License 2.0 (Copyright (c) Meta Platforms, Inc. and affiliates): its full text is in `licenses/SAM-2.1-LICENSE.txt`, and `licenses/MODELS-README.txt` lists the files. Both are also in the folder Mask downloads the models from, `https://pub-b100959e888f4b8cb607e262182f9a07.r2.dev/mask/models/v1/` (`LICENSE.txt` and `README.txt`).

## Main software

| Software | License | Source |
|---|---|---|
| ONNX Runtime (runs the models; `onnxruntime-directml` on Windows) | MIT | https://github.com/microsoft/onnxruntime |
| DirectML (Windows graphics cards, included in `onnxruntime-directml`) | Microsoft's license, included in the package | https://github.com/microsoft/DirectML |
| Gradio (the browser page) | Apache License 2.0 | https://www.gradio.app |
| PyAV, which includes FFmpeg libraries (reads the videos) | BSD 3-Clause (PyAV); LGPL/GPL (FFmpeg) | https://github.com/PyAV-Org/PyAV, https://ffmpeg.org |
| imageio-ffmpeg, which provides an FFmpeg program (writes the exports) | BSD 2-Clause (imageio-ffmpeg); GPL (FFmpeg with x264) | https://github.com/imageio/imageio-ffmpeg, https://ffmpeg.org |
| NumPy | BSD 3-Clause | https://numpy.org |
| Pillow | MIT-CMU | https://python-pillow.org |
| uv, which installs Python and the packages | MIT or Apache License 2.0 | https://github.com/astral-sh/uv |
| Python | Python Software Foundation License | https://www.python.org |

The complete list of packages and exact versions is in `app/requirements/mask.txt`. After installation, each package's license text is in its folder under `envs/`.
