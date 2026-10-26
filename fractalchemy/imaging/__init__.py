from .extract import WeightedColor, extract_palette
from .ordering import STRATEGIES, order_colors
from .plugins import decoder_hint, supported_image_extensions

__all__ = ["STRATEGIES", "WeightedColor", "extract_palette", "decoder_hint", "order_colors", "supported_image_extensions"]
