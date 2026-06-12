"""智能参考图筛选服务。"""

from pathlib import Path

from coupangads.core import config
from coupangads.core.models import ReferenceImage
from coupangads.infra.image import image_to_data_url, load_image_rgb, resize_long_edge
from coupangads.text.parsers import is_suspected_ai_image


def select_best_reference_images(
    image_paths: list[Path],
    count: int = config.REFERENCE_IMAGE_COUNT,
) -> list[ReferenceImage]:
    """
    从实拍图中筛选最佳参考图。

    当前策略（MVP）：
    - 排除疑似 AI 图
    - 按文件大小降序取前 count 张（简单假设：高质量图更大）
    - 加载、缩放、生成 data_url

    未来可替换为模型打分。
    """
    candidates = [
        p
        for p in image_paths
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic", ".webp")
        and not is_suspected_ai_image(p.name)
    ]
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)

    references: list[ReferenceImage] = []
    for path in candidates[:count]:
        try:
            img = load_image_rgb(path)
            img = resize_long_edge(img, config.REFERENCE_IMAGE_MAX_LONG_EDGE)
            references.append(
                ReferenceImage(
                    path=path,
                    filename=path.name,
                    image=img,
                    data_url=image_to_data_url(img),
                )
            )
        except Exception:
            continue

    return references
