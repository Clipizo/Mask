SAM 2.1 models for Mask (https://github.com/Clipizo/Mask), made by Clipizo

These files are Meta's SAM 2.1 models (Segment Anything 2.1,
https://github.com/facebookresearch/sam2), converted to the ONNX format by Clipizo
for Mask and Maskizo. Clipizo changed their file format, precision and graph
layout, not what the models were trained to do:

- *_fp16.onnx: half precision, for Windows graphics cards (DirectML).
- *_coreml.onnx: full precision, rewritten for Core ML; used on Macs and on
  processors.
- sam2_image_*: the models for clicking (tiny, small and large).
- sam2_track_small_*: the model for tracking.

Copyright (c) Meta Platforms, Inc. and affiliates. Licensed under the Apache
License 2.0: see LICENSE.txt in this folder. Mask and Clipizo aren't affiliated
with or endorsed by Meta.

Mask downloads these files by itself; nobody needs to download them by hand.
It checks each one's size (in bytes) and SHA-256:

  sam2_image_tiny_fp16.onnx       65,115,540  0de727f6613d9b1e935a8f3640c7b579c8fd5d87bd345c10157c523b4dacc2f7
  sam2_image_small_fp16.onnx      79,361,003  bf0a35d9ecf5faacc98101ea995f4758b9856753e216d1d187069bd1cf452eed
  sam2_image_large_fp16.onnx     437,184,298  6229ac867f641fdd1e473d1894ca0ead9cb00bfabc45d9cfdab1a3cba1bb79e6
  sam2_track_small_fp16.onnx     105,146,072  5cb07c2ddb28b8848d869321cd4c92e81789a4142fb20096fef5d9fa1f37ae3b
  sam2_image_tiny_coreml.onnx    156,628,033  86fb4d28368402c9f15ef47f34f514d86911b1b120024c9ccf44d6945f82c8f7
  sam2_image_small_coreml.onnx   189,228,483  3a266002b95507babe4e8809562877dde2813454385d0a4c74e0dda5a58c6fcd
  sam2_image_large_coreml.onnx   909,605,347  7b0dcb07c64e0cd3879c9adb581caf93cb5ded5859c90897b64a2e9fe379af71
  sam2_track_small_coreml.onnx   226,999,585  3a2dadf24f814d0b517b09df33529717f7257afea6a6cda74021b9d85aad8278
