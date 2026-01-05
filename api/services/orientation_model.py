"""
ONNX-based orientation classifier service for 0/90/180/270 prediction.
"""

import io
import logging
from typing import Optional, Tuple

import numpy as np
from PIL import Image

try:
    import onnxruntime as ort  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    ort = None  # lazy import guarded by config

logger = logging.getLogger(__name__)


class OrientationClassifier:
    """Lightweight ONNX orientation classifier wrapper."""

    def __init__(self, model_path: Optional[str]):
        self.model_path = model_path
        self._session: Optional["ort.InferenceSession"] = None

    def _ensure_loaded(self) -> bool:
        if self._session is not None:
            return True
        if ort is None:
            logger.warning("onnxruntime not available; orientation model disabled")
            return False
        if not self.model_path:
            logger.warning("No ORIENTATION_MODEL_PATH configured; model disabled")
            return False
        try:
            self._session = ort.InferenceSession(self.model_path, providers=["CPUExecutionProvider"])  # type: ignore[arg-type]
            return True
        except Exception as e:  # pragma: no cover - depends on runtime
            logger.error(f"Failed to load orientation model: {e}")
            return False

    def predict(self, image_bytes: bytes) -> Optional[Tuple[str, float]]:
        """Return (angle_str, confidence) where angle_str in {"0","90","180","270"}."""
        if not self._ensure_loaded():
            return None

        try:
            # Basic preprocessing: resize to 224x224, normalise to [0,1], CHW float32
            with Image.open(io.BytesIO(image_bytes)) as img:
                rgb_img = img.convert("RGB").resize((224, 224))
                arr = np.asarray(rgb_img, dtype=np.float32) / 255.0
                arr = np.transpose(arr, (2, 0, 1))  # CHW
                arr = np.expand_dims(arr, 0)  # NCHW

            session = self._session
            if session is None:
                return None

            inputs = {session.get_inputs()[0].name: arr}
            outputs = session.run(None, inputs)
            logits = outputs[0]  # shape [1,4]
            probs = _softmax(logits[0])
            idx = int(np.argmax(probs))
            angles = ["0", "90", "180", "270"]
            return angles[idx], float(probs[idx])
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Orientation prediction failed: {e}")
            return None


def _softmax(x: np.ndarray) -> np.ndarray:
    x = x - np.max(x)
    exp_x = np.exp(x)
    return exp_x / np.sum(exp_x)
