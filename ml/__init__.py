"""Runtime inference does not import offline training or legacy models."""
from .predictor import SymptoPredictor
__all__ = ["SymptoPredictor"]
