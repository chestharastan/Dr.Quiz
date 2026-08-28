"""
Khmer OCR Recognizer — ResNet + BiLSTM + CTC

Copied from document_system_ocr/backend/app/services/recognizer.py (its
trained model/weights, unchanged) so this folder is self-contained and
doesn't depend on importing another project's `app` package.
"""

import json
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
import torchvision.transforms as T


# ── Model (exactly as in predict.py) ────────────────────────────────────────────

class ResBlock(nn.Module):
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, stride=stride, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
        )
        self.downsample = None
        if stride != 1 or in_ch != out_ch:
            self.downsample = nn.Sequential(
                nn.Conv2d(in_ch, out_ch, 1, stride=stride, bias=False),
                nn.BatchNorm2d(out_ch),
            )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        identity = x
        out = self.conv(x)
        if self.downsample is not None:
            identity = self.downsample(x)
        return self.relu(out + identity)


class ResNetBiLSTMCTC(nn.Module):
    def __init__(self, num_classes, hidden_size=256, num_layers=2, dropout=0.3):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(1, 64, 3, padding=1, bias=False),       # 0
            nn.BatchNorm2d(64),                                 # 1
            nn.ReLU(inplace=True),                              # 2
            nn.MaxPool2d(2, 2),                                 # 3
            nn.Sequential(ResBlock(64, 64, stride=1)),          # 4
            nn.Sequential(ResBlock(64, 128, stride=2)),         # 5
            nn.Sequential(ResBlock(128, 256, stride=1)),        # 6
        )
        self.rnn = nn.LSTM(
            input_size=256 * 16,
            hidden_size=hidden_size,
            num_layers=num_layers,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=False,
        )
        self.classifier = nn.Linear(hidden_size * 2, num_classes)

    def forward(self, x):
        feat = self.cnn(x)                       # [B, 256, H', W']
        b, c, h, w = feat.shape
        seq = feat.permute(3, 0, 1, 2)          # [W', B, C, H']
        seq = seq.reshape(w, b, c * h)           # [W', B, C*H']
        out, _ = self.rnn(seq)                   # [W', B, 2*hidden]
        return self.classifier(out).log_softmax(2)  # [W', B, num_classes]


# ── Charset ───────────────────────────────────────────────────────────────────

def load_charset(path):
    """Build {index -> character} from char.json."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return {i: ch for i, ch in enumerate(data)}

    if isinstance(data, dict):
        known_categories = {"khmer", "latin", "digits", "special"}
        if known_categories & set(data.keys()):
            order = ["khmer", "latin", "digits", "special"]
            all_chars = "".join(data.get(cat, "") for cat in order)
            return {0: "<blank>", **{i + 1: ch for i, ch in enumerate(all_chars)}}

        try:
            return {int(k): v for k, v in data.items()}
        except ValueError:
            pass

        return {v: k for k, v in data.items()}

    raise ValueError(f"Unrecognised charset format in {path}")


# ── Preprocessing ─────────────────────────────────────────────────────────────

_transform = T.Compose([
    T.ToTensor(),
    T.Normalize(mean=[0.5], std=[0.5]),
])

def preprocess(image, img_h=64, img_w=512):
    """
    Preprocess PIL Image or path.
    Returns tensor: [1, 1, H, W]
    """
    if isinstance(image, (str, Path)):
        image = Image.open(image).convert("L")
    elif not isinstance(image, Image.Image):
        raise TypeError(f"Expected PIL Image or path, got {type(image)}")

    image = image.resize((img_w, img_h), Image.BICUBIC)
    return _transform(image).unsqueeze(0)


# ── CTC decode ────────────────────────────────────────────────────────────────

def ctc_decode(log_probs, idx2char, blank=0):
    """Greedy CTC: argmax → collapse repeats → remove blank."""
    indices = log_probs.argmax(dim=1).tolist()
    chars, prev = [], None
    for idx in indices:
        if idx != prev and idx != blank:
            chars.append(idx2char.get(idx, "?"))
        prev = idx
    return "".join(chars)


# ── KhmerRecognizer (API-friendly wrapper) ────────────────────────────────────

class KhmerRecognizer:
    """
    Wrapper for ResNetBiLSTMCTC that handles model loading and inference.
    """

    def __init__(self, model_dir: str, charset_path: str | None = None):
        """
        Args:
            model_dir: Directory containing best_model.pth (and optionally char.json)
            charset_path: Path to char.json (if not in model_dir)
        """
        self.model_dir = Path(model_dir)

        # Resolve paths
        self.model_path = self.model_dir / "best_model.pth"
        if not self.model_path.exists():
            self.model_path = self.model_dir / "last_model.pth"
        self.charset_path = Path(charset_path) if charset_path else self.model_dir / "char.json"

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        if not self.charset_path.exists():
            raise FileNotFoundError(f"Charset not found: {self.charset_path}")

        # Load charset
        self.idx2char = load_charset(self.charset_path)
        self.num_classes = max(self.idx2char.keys()) + 1

        # Build and load model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = ResNetBiLSTMCTC(num_classes=self.num_classes)

        state_dict = torch.load(self.model_path, map_location="cpu")
        if "model_state" in state_dict:
            state_dict = state_dict["model_state"]
        self.model.load_state_dict(state_dict)
        self.model.to(self.device).eval()

        print(f"[KhmerRecognizer] Loaded {self.model_path}")
        print(f"[KhmerRecognizer] Charset {self.charset_path} ({self.num_classes} classes)")
        print(f"[KhmerRecognizer] Device: {self.device}")

    def recognize(self, image) -> str:
        """
        Recognize text from a PIL Image or image path.

        Args:
            image: PIL Image (RGB or L) or file path

        Returns:
            Predicted text string
        """
        # Convert PIL RGB -> grayscale if needed
        if isinstance(image, Image.Image):
            if image.mode != "L":
                image = image.convert("L")

        tensor = preprocess(image).to(self.device)

        with torch.no_grad():
            log_probs = self.model(tensor)[:, 0, :]  # [T, C]

        return ctc_decode(log_probs.cpu(), self.idx2char, blank=0)

    def recognize_batch(self, images: list) -> list[str]:
        """Batch recognition for multiple images."""
        return [self.recognize(img) for img in images]
