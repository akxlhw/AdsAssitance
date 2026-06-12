"""详情页图片生成服务。"""

from pathlib import Path

from coupangads.adapters.base import ImageAdapter
from coupangads.core.logging import get_logger
from coupangads.core.models import ImagePrompt, ReferenceImage

logger = get_logger(__name__)


def generate_detail_images(
    adapter: ImageAdapter,
    prompts: list[ImagePrompt],
    references: list[ReferenceImage],
    output_dir: Path,
    max_images: int | None = None,
    start_from: str | None = None,
) -> list[Path]:
    """
    逐张生成详情页图片。

    - 支持 max_images 限制生成数量
    - 支持 start_from 从指定键恢复（如 A_B4）
    - 单张失败记录并继续
    """
    generated: list[Path] = []
    started = start_from is None

    for idx, prompt in enumerate(prompts):
        if max_images is not None and len(generated) >= max_images:
            break

        if not started:
            if prompt.filename == start_from or f"{prompt.style}_{prompt.block}" == start_from:
                started = True
            else:
                logger.info(f"跳过 {prompt.filename}，等待恢复点 {start_from}")
                continue

        output_path = output_dir / prompt.filename
        logger.info(f"生成图片 {idx + 1}/{len(prompts)}: {prompt.filename}")

        try:
            success = adapter.generate_image(
                prompt=prompt.prompt,
                references=references,
                output_path=output_path,
            )
            if success:
                generated.append(output_path)
                logger.info(f"已保存: {output_path}")
            else:
                logger.error(f"生成失败（无输出）: {prompt.filename}")
        except Exception as exc:
            logger.error(f"生成异常 {prompt.filename}: {exc}")

    return generated
