"""Compatibility shims for craft-text-detector 0.4.3 (unmaintained since ~2022)
against modern torchvision (>=0.13) and numpy (>=2.0):

1. torchvision removed `torchvision.models.vgg.model_urls` and the `pretrained=`
   bool kwarg in favor of `weights=`.
2. numpy 2.x raises instead of silently building an object array from a ragged
   nested sequence of variable-length polygons — craft's own `predict.py` and
   `craft_utils.py` both do `np.array(list_of_variable_length_arrays)` in
   several places, relying on the old (numpy <1.24) silent-object-array
   behavior. Rather than reimplementing each internal call site (fragile
   across package versions), `ragged_array_tolerant()` scopes a narrow
   `np.array` shim to just the `detect_text()` call.

Must be imported before any `from craft_text_detector import ...`.
"""

import contextlib

import numpy as np
import torchvision.models as tv_models
import torchvision.models.vgg as tv_vgg

if not hasattr(tv_vgg, "model_urls"):
    tv_vgg.model_urls = {
        "vgg16_bn": "https://download.pytorch.org/models/vgg16_bn-6c64b313.pth",
    }

if not hasattr(tv_models.vgg16_bn, "_quizdr_patched"):
    _original_vgg16_bn = tv_models.vgg16_bn

    def _patched_vgg16_bn(pretrained: bool = False, **kwargs):
        weights = tv_vgg.VGG16_BN_Weights.IMAGENET1K_V1 if pretrained else None
        kwargs.pop("pretrained", None)
        return _original_vgg16_bn(weights=weights, **kwargs)

    _patched_vgg16_bn._quizdr_patched = True
    tv_models.vgg16_bn = _patched_vgg16_bn


@contextlib.contextmanager
def ragged_array_tolerant():
    """Temporarily make np.array() fall back to dtype=object for ragged
    nested sequences, matching numpy <1.24 behavior that craft-text-detector
    relies on internally. Scope this tightly around craft calls only."""
    original_array = np.array

    def tolerant_array(obj, *args, **kwargs):
        try:
            return original_array(obj, *args, **kwargs)
        except ValueError as exc:
            if "inhomogeneous" in str(exc) and "dtype" not in kwargs:
                return original_array(obj, *args, dtype=object, **kwargs)
            raise

    np.array = tolerant_array
    try:
        yield
    finally:
        np.array = original_array
