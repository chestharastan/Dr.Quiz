"""Recognizers for the QCM cell pipeline:

- KhmerCellRecognizer wraps KhmerRecognizer (line-level CRNN,
  ResNet-BiLSTM-CTC), for the question/choice text cells. Verified against
  ground truth: near-perfect on full Khmer sentence lines, which is its
  training domain.
- TesseractGlyphRecognizer handles the row-number and answer-letter cells.
  Those are short, isolated, single-font-size glyphs (e.g. "421", "B") —
  visually nothing like the sentence lines the CRNN was fine-tuned on, and it
  reliably misreads them (e.g. bold "B" -> Khmer digit "២"). Tesseract, which
  is unreliable on full Khmer text, is accurate on these isolated Latin/digit
  glyphs when scoped with --psm and a char whitelist. Both were verified
  against a hand-checked answer key before wiring in.
- TesseractTextRecognizer and KhmerHFRecognizer are opt-in alternatives to
  KhmerCellRecognizer for the question/choice text cells, selectable via
  --recognizer, for side-by-side comparison against the CRNN default.

All expose `recognize(image: np.ndarray) -> (text, confidence)`.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytesseract
import torch
import torch.nn.functional as F
from PIL import Image
from pytesseract import Output

from qcm.recognizer import KhmerRecognizer, ctc_decode, preprocess


class KhmerCellRecognizer:
    def __init__(self, model_dir: str, charset_path: str | None = None):
        self._rec = KhmerRecognizer(model_dir, charset_path)

    def recognize(self, image: np.ndarray) -> tuple[str, float]:
        if image is None or image.size == 0:
            return "", 0.0

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        tensor = preprocess(Image.fromarray(gray)).to(self._rec.device)

        with torch.no_grad():
            log_probs = self._rec.model(tensor)[:, 0, :]  # [T, C]

        log_probs = log_probs.cpu()
        text = ctc_decode(log_probs, self._rec.idx2char, blank=0)
        confidence = log_probs.exp().max(dim=1).values.mean().item() if log_probs.numel() else 0.0
        return text.strip(), float(confidence)


class TesseractGlyphRecognizer:
    """For short isolated Latin/digit cells only (row number, answer letter)
    — not full text lines, see module docstring.

    No single --psm (page segmentation mode) is reliable across every crop —
    verified on real pages that some rows only resolve under psm 7 and
    others only under psm 8/13, seemingly depending on exact ink-bbox
    padding. Tries each mode in order and keeps the first non-empty result.
    """

    def __init__(self, whitelist: str, psm_modes: tuple[int, ...] = (8, 7, 10, 13), lang: str = "eng"):
        self.whitelist = whitelist
        self.psm_modes = psm_modes
        self.lang = lang

    def _try(self, image: np.ndarray, psm: int) -> tuple[str, float]:
        config = f"--psm {psm} -c tessedit_char_whitelist={self.whitelist}"
        data = pytesseract.image_to_data(image, lang=self.lang, config=config, output_type=Output.DICT)

        words, confs = [], []
        for text, conf in zip(data["text"], data["conf"]):
            text = text.strip()
            if not text:
                continue
            words.append(text)
            conf = float(conf)
            if conf >= 0:
                confs.append(conf)

        joined = "".join(words)
        avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
        return joined, avg_conf

    def _sweep(self, image: np.ndarray) -> tuple[str, float]:
        # These crops are tight ink-bbox glyphs, often <50px tall — Tesseract
        # reliably returns nothing at that native size (verified: a 48x50
        # crop of a lone "C" returns '' at every psm until upscaled). No
        # single scale factor is reliable either — cubic-resize artifacts at
        # a given factor occasionally blank out or misread the same glyph
        # another factor gets right (verified against hand-picked failing
        # crops), so multiple scales are tried like the psm modes are.
        scales = (2, 3, 4, 6) if max(image.shape[:2]) < 150 else (1,)
        for scale in scales:
            scaled = image if scale == 1 else cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            for psm in self.psm_modes:
                text, conf = self._try(scaled, psm)
                if text:
                    return text, conf
        return "", 0.0

    def recognize(self, image: np.ndarray) -> tuple[str, float]:
        if image is None or image.size == 0:
            return "", 0.0

        # Otsu-binarizing first resolved every one of a batch of crops
        # (all the letter "C", oddly) that the raw grayscale/color sweep
        # below couldn't read at any scale/psm — flattening antialiasing
        # noise around the glyph edge seems to matter more than resolution
        # for those. Tried first since it's cheap and was strictly better in
        # that batch; falls back to the raw sweep for anything it doesn't
        # resolve, as a safety net against a bad Otsu threshold elsewhere.
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        text, conf = self._sweep(bw)
        if text:
            return text, conf
        return self._sweep(image)


class TesseractTextRecognizer:
    """Full Khmer text-line recognizer via Tesseract (lang='khm'), as an
    opt-in alternative to KhmerCellRecognizer for the question/choice text
    cells — see this module's docstring: Tesseract tested unreliable on
    full Khmer sentences vs the CRNN, so it is not the default, only
    selectable via --recognizer tesseract.
    """

    def __init__(self, lang: str = "khm+eng", psm: int = 7):
        self.lang = lang
        self.psm = psm

    def recognize(self, image: np.ndarray) -> tuple[str, float]:
        if image is None or image.size == 0:
            return "", 0.0

        config = f"--psm {self.psm}"
        data = pytesseract.image_to_data(image, lang=self.lang, config=config, output_type=Output.DICT)

        words, confs = [], []
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


class KhmerHFRecognizer:
    """Full Khmer text-line recognizer via the Darayut/khmer-text-recognition
    HF model (SE-VGG feature extractor + Transformer encoder/decoder +
    BiLSTM chunk smoother) — a different architecture from
    KhmerCellRecognizer's ResNet-BiLSTM-CTC. Opt-in alternative for the
    question/choice text cells, selectable via --recognizer hf, for
    side-by-side comparison against the CRNN default.

    Loaded from a local model_dir (see download_khmer_hf_model.sh, which
    fetches only the inference-essential files, not the repo's extra .pth
    training checkpoints). That model_dir's own inference.py/modeling code
    is imported directly rather than reimplemented here.

    Requires transformers==4.57.1 (pinned in .venv-khmerocr) — the model's
    trust_remote_code class AttributeErrors under transformers 5.x's
    internal weight-tying API. Run this recognizer with
    .venv-khmerocr/bin/python, not the thaocr env directly.

    Decodes greedily rather than with the repo's beam search so a
    per-character softmax probability is available to average into
    ocr_confidence like the other recognizers (beam search there discards
    per-step probabilities once a beam completes).
    """

    def __init__(self, model_dir: str, max_len: int = 256):
        model_dir = str(Path(model_dir).resolve())
        if model_dir not in sys.path:
            sys.path.insert(0, model_dir)
        from inference import KhmerOCR  # model_dir's own class

        self._ocr = KhmerOCR(model_repo=model_dir)
        self.max_len = max_len

    def recognize(self, image: np.ndarray) -> tuple[str, float]:
        if image is None or image.size == 0:
            return "", 0.0

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        chunks_tensor = self._ocr.preprocess(Image.fromarray(gray))

        device = self._ocr.device
        with torch.no_grad():
            memory = self._ocr.model([chunks_tensor])

            B, T, _ = memory.shape
            memory_mask = torch.zeros((B, T), dtype=torch.bool, device=device)
            generated = [self._ocr.sos_idx]
            step_confs = []
            for _ in range(self.max_len):
                tgt = torch.LongTensor([generated]).to(device)
                logits = self._ocr.model.dec(tgt, memory, memory_mask)
                step_probs = F.softmax(logits[0, -1, :], dim=-1)
                next_token = int(torch.argmax(step_probs).item())
                step_confs.append(step_probs[next_token].item())
                if next_token == self._ocr.eos_idx:
                    break
                generated.append(next_token)

        text = "".join(
            self._ocr.id2char.get(idx, "")
            for idx in generated
            if idx not in (self._ocr.sos_idx, self._ocr.eos_idx, self._ocr.pad_idx, self._ocr.unk_idx)
        )
        confidence = sum(step_confs) / len(step_confs) if step_confs else 0.0
        return text.strip(), float(confidence)
