"""参考图筛选单元测试。"""

from pathlib import Path

from PIL import Image

from coupangads.image_pipeline.reference_selector import select_best_reference_images


def test_select_excludes_ai_named_images(tmp_path: Path) -> None:
    img1 = tmp_path / "IMG_001.jpg"
    img2 = tmp_path / "ai_generated_v2.jpg"
    Image.new("RGB", (100, 100)).save(img1)
    Image.new("RGB", (100, 100)).save(img2)
    refs = select_best_reference_images([img1, img2], count=1)
    assert len(refs) == 1
    assert refs[0].filename == "IMG_001.jpg"
