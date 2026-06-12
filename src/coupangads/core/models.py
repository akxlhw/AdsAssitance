"""核心数据模型。"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass
class ReferenceImage:
    path: Path
    filename: str
    image: Image.Image
    data_url: str | None = None


@dataclass
class ImagePrompt:
    style: str
    screen: str
    block: str
    prompt: str
    filename: str
