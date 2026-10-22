# Third-party components

The `third_party/PaddleOCR` directory contains PaddleOCR v3.0.3 Python implementation files used by inference. Copyright notices remain in their source files; the Apache-2.0 license is included at `third_party/PaddleOCR/LICENSE`. Inference configurations select the PP-OCRv5 model architectures and preprocessing operations.

Standard pretrained model download URLs and SHA256 checksums are recorded in `models/manifest.json`. Model files are optional binary assets and are not included in the source delivery archive.

The optional handwriting detector adapter invokes Ultralytics in a separate Python environment. Ultralytics is not vendored here; its installed distribution retains its own license. A compatible model must be configured by the deployment operator.

Other Python dependency licenses are distributed with their respective packages. This module does not alter third-party copyright or license notices.
