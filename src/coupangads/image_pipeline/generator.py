"""详情页图片生成服务。"""

import threading
import time
from pathlib import Path
from typing import Callable

from coupangads.adapters.base import ImageAdapter
from coupangads.core import config
from coupangads.core.logging import get_logger
from coupangads.core.models import ImagePrompt, ReferenceImage

logger = get_logger(__name__)


def _generate_one(
    adapter: ImageAdapter,
    prompt: ImagePrompt,
    references: list[ReferenceImage],
    output_path: Path,
    timeout_sec: float | None,
) -> bool:
    """生成单张图片，包裹一层 pipeline 级超时。

    超时策略：adapter.generate_image 在 daemon thread 内执行，
    主线程 join(timeout=...)。超时后放弃该图继续下一张。
    被遗弃的 daemon thread 会继续在后台跑（Python 无法强杀线程），
    但 daemon thread 不阻塞进程退出。
    """
    if timeout_sec is None or timeout_sec <= 0:
        return adapter.generate_image(
            prompt=prompt.prompt,
            references=references,
            output_path=output_path,
        )

    result: dict = {"success": False, "exc": None, "done": False}

    def _run() -> None:
        try:
            result["success"] = adapter.generate_image(
                prompt=prompt.prompt,
                references=references,
                output_path=output_path,
            )
        except Exception as exc:  # noqa: BLE001 — 任意异常都记录后透出
            result["exc"] = exc
        finally:
            result["done"] = True

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    worker.join(timeout=timeout_sec)

    if worker.is_alive():
        # 还在跑 = 超时；daemon thread 在后台继续，但不阻塞主流程
        logger.error(
            f"超时 {output_path.name}（>{timeout_sec:.0f}s），跳过本张继续"
        )
        return False

    if result["exc"] is not None:
        raise result["exc"]
    return result["success"]


def generate_detail_images(
    adapter: ImageAdapter,
    prompts: list[ImagePrompt],
    references: list[ReferenceImage],
    output_dir: Path,
    max_images: int | None = None,
    start_from: str | None = None,
    delay: float = 0.0,
    progress_callback: Callable[[int, int, str], None] | None = None,
    abort_callback: Callable[[], None] | None = None,
    per_image_timeout_sec: float | None = None,
) -> list[Path]:
    """
    逐张生成详情页图片。

    - 支持 max_images 限制尝试生成数量
    - 支持 start_from 从指定键恢复（如 A_B4）
    - 单张失败记录并继续
    - 支持 progress_callback(completed_count, total_count, filename) 汇报进度
    - 支持 abort_callback 在每张图片生成前检查是否中止
    - 支持 per_image_timeout_sec 单张超时保护（None=不限，默认走 config）
    """
    if per_image_timeout_sec is None:
        per_image_timeout_sec = float(config.DEFAULT_IMAGE_TIMEOUT_SEC)

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

        if abort_callback is not None:
            abort_callback()

        attempted += 1
        output_path = output_dir / prompt.filename
        logger.info(f"生成图片 {idx + 1}/{len(prompts)}: {prompt.filename}")

        try:
            success = _generate_one(
                adapter, prompt, references, output_path, per_image_timeout_sec
            )
            if success:
                generated.append(output_path)
                logger.info(f"已保存: {output_path}")
                if progress_callback:
                    progress_callback(len(generated), len(prompts), prompt.filename)
            else:
                logger.error(f"生成失败（无输出或超时）: {prompt.filename}")
        except Exception as exc:
            logger.error(f"生成异常 {prompt.filename}: {exc}")

        if delay > 0:
            time.sleep(delay)

    if start_from is not None and not started:
        logger.warning(f"未找到恢复点 {start_from}，没有生成任何图片")

    return generated
