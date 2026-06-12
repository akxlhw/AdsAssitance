"""模型适配器包。"""

from coupangads.adapters.base import ImageAdapter, TextAdapter
from coupangads.adapters.doubao import DoubaoClientAdapter
from coupangads.adapters.gemini import GeminiClientAdapter

__all__ = ["TextAdapter", "ImageAdapter", "GeminiClientAdapter", "DoubaoClientAdapter"]
