"""图像处理单元测试。"""

from pathlib import Path

from PIL import Image

from coupangads.infra.image import load_image_rgb, resize_long_edge


def test_load_image_rgb_converts_rgba(tmp_path: Path) -> None:
    img_path = tmp_path / "rgba.png"
    Image.new("RGBA", (100, 100), (255, 0, 0, 128)).save(img_path)
    loaded = load_image_rgb(img_path)
    assert loaded.mode == "RGB"


def test_resize_long_edge_scales_down() -> None:
    img = Image.new("RGB", (2000, 1000))
    resized = resize_long_edge(img, 800)
    assert max(resized.size) == 800
    assert resized.size[0] == 800


def test_resize_long_edge_keeps_small_image() -> None:
    img = Image.new("RGB", (400, 300))
    resized = resize_long_edge(img, 800)
    assert resized.size == (400, 300)
