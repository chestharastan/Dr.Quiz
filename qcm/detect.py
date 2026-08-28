import qcm._craft_compat as _craft_compat  # noqa: F401 - must import before craft_text_detector

import numpy as np
from craft_text_detector import Craft


class TextDetector:
    """Wraps CRAFT text detection. Load once, call detect() per page image."""

    def __init__(self, cuda: bool = True):
        self._craft = Craft(output_dir=None, crop_type="poly", cuda=cuda)

    def detect(self, image: np.ndarray) -> list[np.ndarray]:
        """Return a list of Nx2 point-array boxes (usually 4-point quads) for
        detected text regions in the given BGR image."""
        with _craft_compat.ragged_array_tolerant():
            result = self._craft.detect_text(image)
        return [np.asarray(box, dtype=np.float64) for box in result["boxes"]]

    def close(self) -> None:
        self._craft.unload_craftnet_model()
        self._craft.unload_refinenet_model()
