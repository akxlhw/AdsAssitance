"""详情页图片生成服务。"""

import time
from pathlib import Path
from typing import Callable

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
    delay: float = 0.0,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[Path]:
    """
    逐张生成详情页图片。

    - 支持 max_images 限制尝试生成数量
    - 支持 start_from 从指定键恢复（如 A_B4）
    - 单张失败记录并继续
    - 支持 progress_callback(completed_count, total_count, filename) 汇报进度
    """
    generated: list[Path] = []
    started = start_from is None
    attempted = 0

    output_dir.mkdir(parents=True, exist_ok=True)

    for idx, prompt in enumerate(prompts):
        if not started:
            if prompt.filename == start_from or f"{prompt.style}_{prompt.block}" == start_from:
                started = True
            else:
                logger.info(f"跳过 {prompt.filename}，等待恢复点 {start_from}")
                continue

        if max_images is not None and attempted >= max_images:
            break

        attempted += 1
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
                if progress_callback:
                    progress_callback(len(generated), len(prompts), prompt.filename)
            else:
                logger.error(f"生成失败（无输出）: {prompt.filename}")
        except Exception as exc:
            logger.error(f"生成异常 {prompt.filename}: {exc}")

        if delay > 0:
            time.sleep(delay)

    if start_from is not None and not started:
        logger.warning(f"未找到恢复点 {start_from}，没有生成任何图片")

    return generated
