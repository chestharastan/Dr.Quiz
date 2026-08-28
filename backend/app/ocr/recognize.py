from typing import Protocol

import numpy as np
import pytesseract
from pytesseract import Output


class Recognizer(Protocol):
    def recognize(self, image: np.ndarray) -> tuple[str, float]:
        """Return (text, confidence in [0, 1]) for a single cropped region."""
        ...


class TesseractRecognizer:
    def __init__(self, lang: str = "khm+eng", psm: int = 6, whitelist: str | None = None):
        self.lang = lang
        self.psm = psm
        self.whitelist = whitelist

    def recognize(self, image: np.ndarray) -> tuple[str, float]:
        config = f"--psm {self.psm}"
        if self.whitelist:
            config += f" -c tessedit_char_whitelist={self.whitelist}"
        data = pytesseract.image_to_data(
            image, lang=self.lang, config=config, output_type=Output.DICT
        )
        words = []
        confs = []
        for text, conf in zip(data["text"], data["conf"]):
            text = text.strip()
            if not text:
                continue
            words.append(text)
            conf = float(conf)
            if conf >= 0:
                confs.append(conf)
        joined = " ".join(words)
        avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
        return joined, avg_conf


_REGISTRY: dict[str, type] = {
    "tesseract": TesseractRecognizer,
}


def get_recognizer(name: str = "tesseract", **kwargs) -> Recognizer:
    if name not in _REGISTRY:
        raise ValueError(f"Unknown recognizer '{name}'. Available: {list(_REGISTRY)}")
    return _REGISTRY[name](**kwargs)
