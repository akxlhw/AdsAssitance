"""图像处理工具。"""

from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()


def load_image_rgb(path: Path) -> Image.Image:
    """加载图片并转换为 RGB 模式。"""
    with Image.open(path) as img:
        if img.mode in ("RGBA", "P"):
            return img.convert("RGB")
        return img.convert("RGB")


def resize_long_edge(img: Image.Image, max_long_edge: int) -> Image.Image:
    """等比缩放，使长边不超过 max_long_edge。"""
    width, height = img.size
    long_edge = max(width, height)
    if long_edge <= max_long_edge:
        return img
    ratio = max_long_edge / long_edge
    new_size = (int(width * ratio), int(height * ratio))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def image_to_data_url(img: Image.Image, fmt: str = "JPEG") -> str:
    """将 PIL Image 编码为 Base64 Data URL。"""
    import base64
    import io

    buffer = io.BytesIO()
    img.save(buffer, format=fmt)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    mime = "image/jpeg" if fmt == "JPEG" else f"image/{fmt.lower()}"
    return f"data:{mime};base64,{b64}"
